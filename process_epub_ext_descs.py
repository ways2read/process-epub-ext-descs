#!/usr/bin/env python3
"""
process-epub-ext-descs

Processes EPUB 3 files to extract extended descriptions and move them
to separate XHTML files with proper linking.
"""

import zipfile
import tempfile
from pathlib import Path
from collections import defaultdict
import re

try:
    from lxml import etree
except ImportError:
    import sys
    print("Error: The 'lxml' library is required but not installed.")
    print("Install it with: pip install lxml")
    sys.exit(1)


class EPUBProcessor:
    """Process EPUB files to extract and relocate extended descriptions."""
    
    NAMESPACES = {
        'xhtml': 'http://www.w3.org/1999/xhtml',
        'epub': 'http://www.idpf.org/2007/ops',
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    
    def __init__(self, start_delimiter="Beginning of extended description", 
                 end_delimiter="End of extended description",
                 normalize_headings=False):
        """
        Initialize processor with configurable delimiters.
        
        Args:
            start_delimiter: Text marking the start of an extended description
            end_delimiter: Text marking the end of an extended description
            normalize_headings: If True, shift heading levels in each
                description so that the highest-level heading becomes h1
        """
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter
        self.normalize_headings = normalize_headings
        self.messages = {
            'success': [],
            'warnings': [],
            'errors': []
        }
        self.description_counter = defaultdict(int)
        
    def process_epub(self, input_path, output_path):
        """
        Process an EPUB file and create a new one with relocated descriptions.
        
        Args:
            input_path: Path to input EPUB file
            output_path: Path for output EPUB file
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract EPUB
            self._extract_epub(input_path, temp_path)
            
            # Find OPF file
            opf_path = self._find_opf(temp_path)
            if not opf_path:
                self.messages['errors'].append("Could not find OPF package document")
                return False
            
            # Parse OPF
            opf_tree = etree.parse(str(opf_path))
            opf_root = opf_tree.getroot()
            
            # Get content directory (where OPF is located)
            content_dir = opf_path.parent
            
            # Get all XHTML content files from manifest
            xhtml_files = self._get_xhtml_files(opf_root, content_dir)
            
            # Process each XHTML file
            new_files = []
            for xhtml_file in xhtml_files:
                result = self._process_xhtml_file(xhtml_file, content_dir)
                if result:
                    new_files.extend(result)
            
            # Update OPF manifest and spine with new files
            if new_files:
                self._update_opf(opf_root, new_files, content_dir)
                opf_tree.write(str(opf_path), encoding='utf-8', 
                              xml_declaration=True, pretty_print=True)
            
            # Create new EPUB
            self._create_epub(temp_path, output_path)
            
            self.messages['success'].append(
                f"Processed {len(xhtml_files)} XHTML files, "
                f"created {len(new_files)} extended description files"
            )
            
        return True
    
    def _extract_epub(self, epub_path, extract_to):
        """Extract EPUB to directory."""
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    
    def _find_opf(self, epub_dir):
        """Find the OPF package document."""
        # Check container.xml
        container_path = epub_dir / 'META-INF' / 'container.xml'
        if container_path.exists():
            tree = etree.parse(str(container_path))
            rootfile = tree.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
            if rootfile is not None:
                opf_path = epub_dir / rootfile.get('full-path')
                if opf_path.exists():
                    return opf_path
        
        # Fallback: search for .opf files
        opf_files = list(epub_dir.rglob('*.opf'))
        if opf_files:
            return opf_files[0]
        
        return None
    
    def _get_xhtml_files(self, opf_root, content_dir):
        """Get list of XHTML content files from OPF manifest."""
        xhtml_files = []
        
        # Find all manifest items with XHTML media type
        manifest = opf_root.find('.//opf:manifest', self.NAMESPACES)
        if manifest is not None:
            for item in manifest.findall('opf:item', self.NAMESPACES):
                media_type = item.get('media-type', '')
                if 'xhtml' in media_type or 'html' in media_type:
                    href = item.get('href')
                    if href:
                        file_path = content_dir / href
                        if file_path.exists():
                            xhtml_files.append(file_path)
        
        return xhtml_files
    
    def _process_xhtml_file(self, xhtml_path, content_dir):
        """
        Process a single XHTML file to extract extended descriptions.
        
        Returns:
            List of (filepath, properties) tuples for created files,
            or None if no descriptions found.
        """
        try:
            # Parse XHTML
            parser = etree.XMLParser(remove_blank_text=False, recover=True)
            tree = etree.parse(str(xhtml_path), parser)
            root = tree.getroot()
            
            # Detect language from page metadata
            lang = self._detect_language(root)
            
            # Find delimiter pairs
            pairs = self._find_delimiter_pairs(root)
            
            if not pairs:
                return None
            
            new_files = []
            
            # Process each pair
            for start_elem, end_elem in pairs:
                # Find associated image
                img_elem = self._find_associated_image(start_elem, root)
                
                if img_elem is None:
                    self.messages['errors'].append(
                        f"No associated image found for extended description in {xhtml_path.name}"
                    )
                    continue
                
                # Extract content between delimiters
                content = self._extract_description_content(start_elem, end_elem)
                
                # Detect special content properties before elements are moved
                properties = self._detect_content_properties(content)
                
                # Generate IDs and filename
                img_src = img_elem.get('src', '')
                img_id, desc_filename, desc_id = self._generate_description_ids(img_src, xhtml_path)
                
                # Set ID on image for backlinking
                img_elem.set('id', img_id)
                
                # Create extended description file
                desc_file_path = xhtml_path.parent / desc_filename
                self._create_description_file(
                    desc_file_path, img_elem, content, 
                    xhtml_path.name, img_id, desc_id, lang
                )
                new_files.append((desc_file_path, properties))
                
                # Replace delimiters and content with link
                self._replace_with_link(start_elem, end_elem, desc_filename, 
                                       content, img_elem, img_id, desc_id)
                
                self.messages['success'].append(
                    f"Created extended description: {desc_filename}"
                )
            
            # Save modified XHTML
            tree.write(str(xhtml_path), encoding='utf-8',
                      xml_declaration=True, method='xml')
            
            return new_files
            
        except Exception as e:
            self.messages['errors'].append(
                f"Error processing {xhtml_path.name}: {str(e)}"
            )
            return None
    
    def _detect_language(self, root):
        """
        Detect the language of an XHTML document from its root element.
        
        Checks for xml:lang and lang attributes on the <html> element.
        
        Returns:
            Language code string (e.g., 'en', 'fr'), or 'en' as fallback.
        """
        # Check xml:lang attribute first (preferred in XHTML)
        lang = root.get('{http://www.w3.org/XML/1998/namespace}lang')
        if lang:
            return lang
        
        # Fall back to lang attribute
        lang = root.get('lang')
        if lang:
            return lang
        
        # Default fallback
        self.messages['warnings'].append(
            "No language attribute found on source document; defaulting to 'en'"
        )
        return 'en'
    
    def _find_delimiter_pairs(self, root):
        """
        Find and validate delimiter pairs in the document.
        
        Returns:
            List of (start_element, end_element) tuples
        """
        pairs = []
        
        # Find all paragraphs
        paragraphs = root.xpath('.//xhtml:p', namespaces=self.NAMESPACES)
        
        # Identify start and end delimiters
        start_elements = []
        end_elements = []
        
        for p in paragraphs:
            text = self._get_text_content(p).strip()
            if text == self.start_delimiter:
                start_elements.append(p)
            elif text == self.end_delimiter:
                end_elements.append(p)
        
        # Validate pairing
        if len(start_elements) != len(end_elements):
            self.messages['errors'].append(
                f"Mismatched delimiters: {len(start_elements)} start, "
                f"{len(end_elements)} end"
            )
            return []
        
        # Match pairs in document order
        for start, end in zip(start_elements, end_elements):
            # Verify end comes after start
            start_index = root.xpath('.//xhtml:p', namespaces=self.NAMESPACES).index(start)
            end_index = root.xpath('.//xhtml:p', namespaces=self.NAMESPACES).index(end)
            
            if end_index <= start_index:
                self.messages['errors'].append(
                    "End delimiter appears before start delimiter"
                )
                continue
            
            pairs.append((start, end))
        
        return pairs
    
    def _get_text_content(self, element):
        """Get text content of an element, joining all text nodes."""
        return ''.join(element.itertext())
    
    def _find_associated_image(self, start_elem, root):
        """
        Find the image associated with an extended description.
        
        Searches backwards through the DOM from the start delimiter.
        """
        # Get all images in document
        all_images = root.xpath('.//xhtml:img', namespaces=self.NAMESPACES)
        
        if not all_images:
            return None
        
        # Get all elements in document order
        all_elements = list(root.iter())
        
        try:
            start_index = all_elements.index(start_elem)
        except ValueError:
            return None
        
        # Search backwards from start delimiter for nearest image
        for i in range(start_index - 1, -1, -1):
            elem = all_elements[i]
            if elem.tag == '{http://www.w3.org/1999/xhtml}img':
                return elem
            # Also check if this element contains an image
            imgs = elem.findall('.//xhtml:img', self.NAMESPACES)
            if imgs:
                return imgs[-1]  # Return the last (closest) image
        
        return None
    
    def _find_common_ancestor(self, elem1, elem2):
        """Find the lowest common ancestor of two elements."""
        ancestors1 = []
        current = elem1.getparent()
        while current is not None:
            ancestors1.append(current)
            current = current.getparent()
        ancestors1_ids = {id(a) for a in ancestors1}
        
        current = elem2.getparent()
        while current is not None:
            if id(current) in ancestors1_ids:
                return current
            current = current.getparent()
        return None
    
    def _find_ancestor_child(self, ancestor, descendant):
        """Find the direct child of ancestor that is or contains the descendant."""
        current = descendant
        while current is not None:
            if current.getparent() is ancestor:
                return current
            current = current.getparent()
        return None
    
    def _extract_description_content(self, start_elem, end_elem):
        """
        Extract all content between start and end delimiter elements.
        
        Handles both the simple case (same parent) and arbitrarily deep
        cross-nesting where headings inside the description create nested
        sections.
        
        Returns:
            List of elements between the delimiters
        """
        start_parent = start_elem.getparent()
        end_parent = end_elem.getparent()
        
        if start_parent is None:
            return []
        
        if start_parent is end_parent:
            # Simple case: delimiters share the same parent
            children = list(start_parent)
            try:
                start_index = children.index(start_elem)
                end_index = children.index(end_elem)
            except ValueError:
                return []
            return children[start_index + 1:end_index]
        
        # Cross-parent case: delimiters are at different nesting levels
        common = self._find_common_ancestor(start_elem, end_elem)
        if common is None:
            return []
        
        start_branch = self._find_ancestor_child(common, start_elem)
        end_branch = self._find_ancestor_child(common, end_elem)
        
        if start_branch is None or end_branch is None:
            return []
        
        content = []
        
        # Start side: walk up from start_elem to start_branch, collecting
        # trailing siblings at each nesting level
        current = start_elem
        while current is not start_branch:
            parent = current.getparent()
            siblings = list(parent)
            idx = siblings.index(current)
            content.extend(siblings[idx + 1:])
            current = parent
        
        # Middle: full subtrees between start_branch and end_branch
        ca_children = list(common)
        try:
            sbi = ca_children.index(start_branch)
            ebi = ca_children.index(end_branch)
        except ValueError:
            return []
        content.extend(ca_children[sbi + 1:ebi])
        
        # End side: walk down from end_branch to end_elem, collecting
        # leading siblings at each nesting level
        path_to_end = []
        current = end_elem
        while current is not end_branch:
            path_to_end.append(current)
            current = current.getparent()
        path_to_end.append(end_branch)
        path_to_end.reverse()
        
        for i in range(len(path_to_end) - 1):
            node = path_to_end[i]
            next_on_path = path_to_end[i + 1]
            children = list(node)
            idx = children.index(next_on_path)
            content.extend(children[:idx])
        
        return content
    
    def _generate_description_ids(self, img_src, xhtml_path):
        """
        Generate unique IDs for the extended description pattern.
        
        Args:
            img_src: Source path of the image
            xhtml_path: Path to the XHTML file being processed
            
        Returns:
            Tuple of (img_id, desc_filename, desc_id)
            - img_id: ID for the image element (e.g., "img3" or "diagram-001")
            - desc_filename: Filename for the extended description file
            - desc_id: ID for the section in the extended description file
        """
        # Extract image filename
        img_name = Path(img_src).stem if img_src else 'image'
        
        # Sanitize for use in ID
        img_name = re.sub(r'[^a-zA-Z0-9-]', '-', img_name)
        
        # Increment counter for this image
        self.description_counter[img_name] += 1
        counter = self.description_counter[img_name]
        
        # Generate base ID
        base_id = f"{img_name}-{counter:03d}"
        
        # Generate all three IDs
        img_id = base_id  # e.g., "diagram-001"
        desc_filename = f"desc-{base_id}.xhtml"  # e.g., "desc-diagram-001.xhtml"
        desc_id = f"extended-description-{base_id}"  # e.g., "extended-description-diagram-001"
        
        return img_id, desc_filename, desc_id
    
    def _detect_content_properties(self, content):
        """
        Detect EPUB content properties (e.g. mathml, svg) in description content.
        
        Must be called before elements are moved to the description file.
        
        Returns:
            Set of OPF property strings needed for this content.
        """
        MATHML_NS = 'http://www.w3.org/1998/Math/MathML'
        SVG_NS = 'http://www.w3.org/2000/svg'
        
        properties = set()
        for elem in content:
            for e in elem.iter():
                tag = e.tag
                if not isinstance(tag, str):
                    continue
                if tag.startswith('{' + MATHML_NS + '}'):
                    properties.add('mathml')
                elif tag.startswith('{' + SVG_NS + '}'):
                    properties.add('svg')
                if 'mathml' in properties and 'svg' in properties:
                    return properties
        return properties
    
    _HEADING_RE = re.compile(r'^\{http://www\.w3\.org/1999/xhtml\}h([1-6])$')

    def _normalize_heading_levels(self, content):
        """
        Shift heading levels so the highest-level heading starts at h1.
        
        Scans all existing XHTML headings (h1-h6) in the content elements
        and their descendants, finds the minimum level, and adjusts every
        heading by that offset.  Only real heading elements are affected;
        markdown-style headings in <p> elements are left untouched so that
        user intent is preserved when they are converted later.
        """
        XHTML_NS = 'http://www.w3.org/1999/xhtml'
        headings = []
        min_level = 7

        for elem in content:
            for e in elem.iter():
                m = self._HEADING_RE.match(e.tag)
                if m:
                    level = int(m.group(1))
                    headings.append((e, level))
                    min_level = min(min_level, level)

        if not headings or min_level <= 1:
            return

        offset = min_level - 1
        for elem, level in headings:
            elem.tag = f'{{{XHTML_NS}}}h{level - offset}'

    def _convert_markdown_heading(self, elem):
        """
        Convert a paragraph with markdown-style heading markup to an XHTML heading.
        
        If a <p> element's text starts with 1-6 '#' characters followed by a space,
        the element is converted in-place to the corresponding <h1>-<h6> element.
        All child elements (inline markup like <b>, <i>, etc.) are preserved.
        
        Examples:
            <p># Title</p>      → <h1>Title</h1>
            <p>## Section</p>   → <h2>Section</h2>
            <p>### <b>Bold</b></p> → <h3><b>Bold</b></h3>
        """
        XHTML_P = '{http://www.w3.org/1999/xhtml}p'
        
        if elem.tag != XHTML_P:
            return
        
        text = elem.text or ''
        match = re.match(r'^(#{1,6})\s+', text)
        if not match:
            return
        
        level = len(match.group(1))
        elem.tag = f'{{http://www.w3.org/1999/xhtml}}h{level}'
        elem.text = text[match.end():]
    
    def _create_description_file(self, filepath, img_elem, content, 
                                 source_filename, img_id, desc_id, lang='en'):
        """Create a new XHTML file with the extended description."""
        # Create root structure
        html = etree.Element(
            '{http://www.w3.org/1999/xhtml}html',
            nsmap={None: 'http://www.w3.org/1999/xhtml'}
        )
        html.set('{http://www.w3.org/XML/1998/namespace}lang', lang)
        
        # Head
        head = etree.SubElement(html, 'head')
        title = etree.SubElement(head, 'title')
        title.text = 'Extended Description'
        
        # Body
        body = etree.SubElement(html, 'body')
        
        # Section wrapper with ID matching the link's href fragment
        section = etree.SubElement(body, 'section')
        section.set('id', desc_id)
        
        # Add image (copy of original) marked as presentational
        img_copy = etree.Element('img')
        img_copy.set('role', 'presentation')
        img_copy.set('alt', '')
        # Copy src and other non-semantic attributes
        if 'src' in img_elem.attrib:
            img_copy.set('src', img_elem.get('src'))
        if 'class' in img_elem.attrib:
            img_copy.set('class', img_elem.get('class'))
        if 'style' in img_elem.attrib:
            img_copy.set('style', img_elem.get('style'))
        section.append(img_copy)
        
        # Normalize heading levels before markdown conversion so that
        # existing XHTML headings (e.g. h4, h5) are shifted to start at
        # h1, while markdown headings keep the user's explicit levels.
        if self.normalize_headings:
            self._normalize_heading_levels(content)
        
        # Add extended description content, converting markdown headings
        for elem in content:
            self._convert_markdown_heading(elem)
            section.append(elem)
        
        # Add backlink with doc-backlink role
        backlink_p = etree.SubElement(section, 'p')
        backlink = etree.SubElement(backlink_p, 'a')
        backlink.set('role', 'doc-backlink')
        backlink.set('href', f"{source_filename}#{img_id}")
        backlink.text = 'Return to content'
        
        # Write file
        tree = etree.ElementTree(html)
        tree.write(str(filepath), encoding='utf-8',
                  xml_declaration=True, method='xml', pretty_print=True)
    
    def _replace_with_link(self, start_elem, end_elem, desc_filename, content, 
                          img_elem, img_id, desc_id):
        """
        Replace delimiter paragraphs and content with a link.
        
        Handles both the simple case (same parent) and the cross-nesting case
        where the end delimiter is inside a nested section. In the cross-nesting
        case, any content remaining after the end delimiter in its container
        hierarchy is promoted up to the common ancestor, and the emptied
        container branch is removed.
        """
        start_parent = start_elem.getparent()
        end_parent = end_elem.getparent()
        
        if start_parent is None:
            return
        
        # Generate link ID
        link_id = f"anchor-extended-description-{img_id}"
        
        # Update image with aria-details pointing to link
        img_elem.set('aria-details', link_id)
        
        # Create link paragraph
        link_p = etree.Element('{http://www.w3.org/1999/xhtml}p')
        link = etree.SubElement(link_p, '{http://www.w3.org/1999/xhtml}a')
        link.set('id', link_id)
        link.set('href', f"{desc_filename}#{desc_id}")
        link.text = 'Extended description'
        
        if start_parent is end_parent:
            # Simple case: delimiters share the same parent
            parent = start_parent
            start_index = list(parent).index(start_elem)
            parent.insert(start_index, link_p)
            parent.remove(start_elem)
            for elem in content:
                if elem.getparent() is parent:
                    parent.remove(elem)
            parent.remove(end_elem)
            return
        
        # Cross-parent case
        common = self._find_common_ancestor(start_elem, end_elem)
        if common is None:
            return
        
        start_branch = self._find_ancestor_child(common, start_elem)
        end_branch = self._find_ancestor_child(common, end_elem)
        
        if start_branch is None or end_branch is None:
            return
        
        # --- Phase 1: Collect trailing content before mutations ---
        # Walk from end_elem up to end_branch, collecting siblings that
        # come after the current element at each nesting level.  These
        # follow the extended description and must be preserved.
        after_content = []
        if end_branch is not end_elem:
            current = end_elem
            while True:
                parent = current.getparent()
                siblings = list(parent)
                idx = siblings.index(current)
                after_content.extend(siblings[idx + 1:])
                if parent is end_branch:
                    break
                current = parent
        
        # --- Phase 2: Mutate the source tree ---
        
        # Insert link at start_elem's position
        if start_branch is start_elem:
            si = list(common).index(start_elem)
            common.insert(si, link_p)
            common.remove(start_elem)
        else:
            si = list(start_parent).index(start_elem)
            start_parent.insert(si, link_p)
            start_parent.remove(start_elem)
        
        # Remove end delimiter
        if end_elem.getparent() is not None:
            end_elem.getparent().remove(end_elem)
        
        # Remove end_branch from common ancestor (its description content
        # has already been moved to the description file by lxml append;
        # only empty wrapper sections and trailing content remain)
        if end_branch.getparent() is common:
            common.remove(end_branch)
        
        # Promote trailing content to the common ancestor level,
        # inserting right after the link
        insert_pos = list(common).index(link_p) + 1
        for i, elem in enumerate(after_content):
            if elem.getparent() is not None:
                elem.getparent().remove(elem)
            common.insert(insert_pos + i, elem)
    
    def _update_opf(self, opf_root, new_files, content_dir):
        """Add new extended description files to OPF manifest and spine."""
        manifest = opf_root.find('.//opf:manifest', self.NAMESPACES)
        if manifest is None:
            return
        
        spine = opf_root.find('.//opf:spine', self.NAMESPACES)
        
        # Find highest existing ID number
        max_id = 0
        for item in manifest.findall('opf:item', self.NAMESPACES):
            item_id = item.get('id', '')
            match = re.search(r'(\d+)$', item_id)
            if match:
                max_id = max(max_id, int(match.group(1)))
        
        # Add new items to manifest and spine
        for new_file, properties in new_files:
            # Calculate relative path from OPF location
            try:
                rel_path = new_file.relative_to(content_dir)
            except ValueError:
                rel_path = new_file.name
            
            max_id += 1
            item_id = f'desc-{max_id:03d}'
            
            item = etree.SubElement(manifest, '{http://www.idpf.org/2007/opf}item')
            item.set('id', item_id)
            item.set('href', str(rel_path).replace('\\', '/'))
            item.set('media-type', 'application/xhtml+xml')
            if properties:
                item.set('properties', ' '.join(sorted(properties)))
            
            # Add to spine as non-linear
            if spine is not None:
                itemref = etree.SubElement(spine, '{http://www.idpf.org/2007/opf}itemref')
                itemref.set('idref', item_id)
                itemref.set('linear', 'no')
    
    def _create_epub(self, source_dir, output_path):
        """Create EPUB file with proper structure."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype must be first and uncompressed
            mimetype_path = source_dir / 'mimetype'
            if mimetype_path.exists():
                epub.write(mimetype_path, 'mimetype', 
                          compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for file_path in source_dir.rglob('*'):
                if file_path.is_file() and file_path.name != 'mimetype':
                    arcname = str(file_path.relative_to(source_dir)).replace('\\', '/')
                    epub.write(file_path, arcname)
    
    def get_report(self):
        """Generate processing report."""
        report = []
        report.append("=" * 60)
        report.append("EPUB Extended Description Processing Report")
        report.append("=" * 60)
        
        if self.messages['success']:
            report.append("\nSUCCESS:")
            for msg in self.messages['success']:
                report.append(f"  ✓ {msg}")
        
        if self.messages['warnings']:
            report.append("\nWARNINGS:")
            for msg in self.messages['warnings']:
                report.append(f"  ⚠ {msg}")
        
        if self.messages['errors']:
            report.append("\nERRORs:")
            for msg in self.messages['errors']:
                report.append(f"  ✗ {msg}")
        
        report.append("\n" + "=" * 60)
        
        return '\n'.join(report)


def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process EPUB 3 files to extract extended descriptions '
                    'into separate XHTML files with proper linking.'
    )
    parser.add_argument('input', help='Path to the input EPUB file')
    parser.add_argument('output', help='Path for the output EPUB file')
    parser.add_argument(
        '--start-delim',
        default='Beginning of extended description',
        help='Text marking the start of an extended description '
             '(default: "Beginning of extended description")'
    )
    parser.add_argument(
        '--end-delim',
        default='End of extended description',
        help='Text marking the end of an extended description '
             '(default: "End of extended description")'
    )
    parser.add_argument(
        '--normalize-headings',
        action='store_true',
        help='Shift heading levels in each description so the '
             'highest-level heading becomes h1'
    )
    
    args = parser.parse_args()
    
    processor = EPUBProcessor(
        start_delimiter=args.start_delim,
        end_delimiter=args.end_delim,
        normalize_headings=args.normalize_headings,
    )
    success = processor.process_epub(args.input, args.output)
    
    print(processor.get_report())
    
    raise SystemExit(0 if success else 1)


if __name__ == '__main__':
    main()
