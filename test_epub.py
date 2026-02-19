#!/usr/bin/env python3
"""
EPUB Validation and Testing Script

Validates that processed EPUB files are well-formed and contain
expected extended description files.
"""

import zipfile
from pathlib import Path
from lxml import etree


def validate_epub(epub_path):
    """
    Validate an EPUB file structure.
    
    Returns:
        Tuple of (is_valid, messages)
    """
    messages = []
    is_valid = True
    
    try:
        # Check if file exists
        if not Path(epub_path).exists():
            return False, ["File does not exist"]
        
        # Check if it's a valid zip file
        if not zipfile.is_zipfile(epub_path):
            return False, ["Not a valid ZIP file"]
        
        with zipfile.ZipFile(epub_path, 'r') as epub:
            # Check mimetype
            if 'mimetype' not in epub.namelist():
                messages.append("ERROR: Missing mimetype file")
                is_valid = False
            else:
                mimetype = epub.read('mimetype').decode('utf-8')
                if mimetype != 'application/epub+zip':
                    messages.append(f"ERROR: Invalid mimetype: {mimetype}")
                    is_valid = False
                else:
                    messages.append("✓ Valid mimetype")
            
            # Check container.xml
            container_path = 'META-INF/container.xml'
            if container_path not in epub.namelist():
                messages.append("ERROR: Missing META-INF/container.xml")
                is_valid = False
            else:
                messages.append("✓ Found container.xml")
                
                # Parse container to find OPF
                container_xml = epub.read(container_path)
                container_tree = etree.fromstring(container_xml)
                
                ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
                rootfile = container_tree.find('.//container:rootfile', ns)
                
                if rootfile is None:
                    messages.append("ERROR: No rootfile in container.xml")
                    is_valid = False
                else:
                    opf_path = rootfile.get('full-path')
                    messages.append(f"✓ OPF path: {opf_path}")
                    
                    # Check OPF exists
                    if opf_path not in epub.namelist():
                        messages.append(f"ERROR: OPF file not found: {opf_path}")
                        is_valid = False
                    else:
                        # Parse OPF
                        opf_xml = epub.read(opf_path)
                        opf_tree = etree.fromstring(opf_xml)
                        
                        ns = {'opf': 'http://www.idpf.org/2007/opf'}
                        
                        # Check for extended description files
                        manifest = opf_tree.find('.//opf:manifest', ns)
                        if manifest is not None:
                            desc_items = [
                                item for item in manifest.findall('.//opf:item', ns)
                                if 'desc-' in item.get('href', '')
                            ]
                            
                            if desc_items:
                                messages.append(f"✓ Found {len(desc_items)} extended description files in manifest:")
                                for item in desc_items:
                                    href = item.get('href')
                                    item_id = item.get('id')
                                    messages.append(f"  - {href} (id: {item_id})")
                                    
                                    # Verify file exists in EPUB
                                    opf_dir = Path(opf_path).parent
                                    full_path = str(opf_dir / href)
                                    
                                    if full_path in epub.namelist():
                                        # Check if it's valid XHTML
                                        try:
                                            xhtml = epub.read(full_path)
                                            xhtml_tree = etree.fromstring(xhtml)
                                            messages.append(f"    ✓ Valid XHTML")
                                        except Exception as e:
                                            messages.append(f"    ERROR: Invalid XHTML: {e}")
                                            is_valid = False
                                    else:
                                        messages.append(f"    ERROR: File not found in EPUB")
                                        is_valid = False
                            else:
                                messages.append("ℹ No extended description files found")
                        
                        # Check spine (desc files should NOT be in spine)
                        spine = opf_tree.find('.//opf:spine', ns)
                        if spine is not None:
                            spine_refs = spine.findall('.//opf:itemref', ns)
                            spine_ids = [ref.get('idref') for ref in spine_refs]
                            
                            desc_in_spine = [
                                sid for sid in spine_ids 
                                if sid and 'desc-' in sid
                            ]
                            
                            if desc_in_spine:
                                messages.append(f"WARNING: Extended descriptions found in spine: {desc_in_spine}")
                                messages.append("         (They should be in manifest only)")
                            else:
                                messages.append("✓ Extended descriptions not in spine (correct)")
        
        return is_valid, messages
        
    except Exception as e:
        return False, [f"ERROR: {str(e)}"]


def test_extended_descriptions(epub_path):
    """
    Test that extended description files have expected structure.
    """
    messages = []
    
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub:
            # Find all desc-*.xhtml files
            desc_files = [f for f in epub.namelist() if 'desc-' in f and f.endswith('.xhtml')]
            
            messages.append(f"\nTesting {len(desc_files)} extended description files:")
            
            for desc_file in desc_files:
                messages.append(f"\n  {desc_file}:")
                
                try:
                    xhtml = epub.read(desc_file)
                    tree = etree.fromstring(xhtml)
                    
                    ns = {'xhtml': 'http://www.w3.org/1999/xhtml'}
                    
                    # Check for image
                    imgs = tree.findall('.//xhtml:img', ns)
                    if imgs:
                        messages.append(f"    ✓ Contains {len(imgs)} image(s)")
                        # Check for presentational image
                        for img in imgs:
                            role = img.get('role', '')
                            alt = img.get('alt', None)
                            if role == 'presentation' and alt == '':
                                messages.append(f"      ✓ Presentational image (role='presentation', alt='')")
                                break
                    else:
                        messages.append(f"    WARNING: No images found")
                    
                    # Check for section wrapper
                    sections = tree.findall('.//xhtml:section', ns)
                    if sections:
                        messages.append(f"    ✓ Contains section wrapper(s)")
                        
                        for section in sections:
                            section_id = section.get('id', '')
                            if section_id:
                                messages.append(f"      Section ID: {section_id}")
                            
                            # Count elements in section
                            elem_count = len(list(section.iter()))
                            messages.append(f"      Contains {elem_count} elements")
                    else:
                        messages.append(f"    WARNING: No section wrapper found")
                    
                    # Check for backlink
                    links = tree.findall('.//xhtml:a', ns)
                    backlinks = [link for link in links if 'href' in link.attrib and '#' in link.get('href')]
                    
                    if backlinks:
                        messages.append(f"    ✓ Contains backlink(s): {[link.get('href') for link in backlinks]}")
                        # Check for doc-backlink role
                        for link in backlinks:
                            role = link.get('role', '')
                            if role == 'doc-backlink':
                                messages.append(f"      ✓ Backlink has role='doc-backlink'")
                                break
                    else:
                        messages.append(f"    WARNING: No backlink found")
                    
                except Exception as e:
                    messages.append(f"    ERROR: {str(e)}")
        
        return messages
        
    except Exception as e:
        return [f"ERROR: {str(e)}"]


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_epub.py <epub_file>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    
    print("=" * 60)
    print("EPUB VALIDATION TEST")
    print("=" * 60)
    print(f"File: {epub_path}\n")
    
    # Validate structure
    is_valid, messages = validate_epub(epub_path)
    
    for msg in messages:
        print(msg)
    
    # Test extended descriptions
    desc_messages = test_extended_descriptions(epub_path)
    for msg in desc_messages:
        print(msg)
    
    print("\n" + "=" * 60)
    if is_valid:
        print("RESULT: VALID ✓")
    else:
        print("RESULT: INVALID ✗")
    print("=" * 60)
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
