# Accessibility Pattern Documentation
## process-epub-ext-descs

## Overview

This processor implements the WCAG-compliant pattern for extended descriptions in EPUB 3, using `aria-details`, proper linking, and semantic roles for optimal accessibility.

## The Pattern

### In the Original Content File

Each image that has an extended description gets:

1. **Unique ID** - For backlinking from the extended description
2. **aria-details attribute** - Points to the link that leads to the extended description

The link to the extended description has:

1. **Unique ID** - Referenced by the image's `aria-details` attribute
2. **href with fragment** - Points to the section in the extended description file

**Example:**
```html
<img id="diagram-001" 
     aria-details="anchor-extended-description-diagram-001"
     src="images/diagram.jpg" 
     alt="A cross-section view showing oxygen-rich blood flow between heart and lungs"/>

<p>
  <a id="anchor-extended-description-diagram-001" 
     href="desc-diagram-001.xhtml#extended-description-diagram-001">
    Extended description
  </a>
</p>
```

### In the Extended Description File

The extended description file contains:

1. **Section wrapper** - With ID matching the fragment in the link's href
2. **Presentational image** - Copy of original with `role="presentation"` and `alt=""`
3. **Description content** - The extracted rich content (paragraphs, lists, tables, etc.)
4. **Backlink** - With `role="doc-backlink"` pointing to the original image

**Example (desc-diagram-001.xhtml):**
```html
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
    <title>Extended Description</title>
  </head>
  <body>
    <section id="extended-description-diagram-001">
      <!-- Presentational image for visual reference -->
      <img role="presentation" alt="" src="images/diagram.jpg"/>
      
      <!-- Extended description content -->
      <p>
        This diagram shows a cross-section view of the circulatory system, 
        specifically the flow of oxygen-rich blood between the heart and lungs.
      </p>
      
      <p>Key components include:</p>
      <ul>
        <li><strong>Left atrium</strong>: Receives oxygen-rich blood from the lungs</li>
        <li><strong>Left ventricle</strong>: Pumps blood to the body</li>
        <li><strong>Pulmonary veins</strong>: Carry oxygenated blood from lungs to heart</li>
      </ul>
      
      <p>
        The arrows in red indicate the direction of blood flow, showing the path 
        from the pulmonary veins through the left side of the heart.
      </p>
      
      <!-- Backlink to return to original location -->
      <p>
        <a role="doc-backlink" href="chapter01.xhtml#diagram-001">
          Return to content
        </a>
      </p>
    </section>
  </body>
</html>
```

## ID Naming Convention

The processor uses a consistent naming pattern:

| Element | ID Format | Example |
|---------|-----------|---------|
| Image | `{image-name}-{counter}` | `diagram-001` |
| Link anchor | `anchor-extended-description-{image-id}` | `anchor-extended-description-diagram-001` |
| Section wrapper | `extended-description-{image-id}` | `extended-description-diagram-001` |
| File name | `desc-{image-id}.xhtml` | `desc-diagram-001.xhtml` |

## Why This Pattern?

### 1. aria-details Attribute

The `aria-details` attribute creates a programmatic association between the image and its extended description. Screen readers can:
- Announce that extended description is available
- Allow users to navigate directly to the description
- Provide keyboard shortcuts to access descriptions

### 2. Link with Unique ID

The link gets its own ID so that:
- The image's `aria-details` can reference it
- Screen readers can announce the relationship
- Users can navigate bidirectionally

### 3. Section Wrapper

The `section` element:
- Provides semantic structure
- Has an ID for direct linking
- Allows proper navigation context
- Groups related content logically

### 4. Presentational Image

The image in the extended description file has:
- `role="presentation"` - Tells screen readers to ignore it
- `alt=""` - Empty alt text (not null/missing)
- Visual attributes preserved (src, class, style)

**Why?** 
- Screen readers already announced the image in the main content
- The image here is only for visual reference
- Prevents double-announcement of the same image
- Sighted users can still see the image for context

### 5. doc-backlink Role

The `role="doc-backlink"` attribute:
- Identifies the link as a backlink semantically
- Helps screen readers announce it appropriately
- Supports better navigation patterns
- Follows DPUB-ARIA specification

## Benefits for Different Users

### Screen Reader Users
- `aria-details` announces extended description availability
- Can navigate directly to full description
- `doc-backlink` makes return navigation clear
- No duplicate image announcements

### Keyboard Users
- Link is keyboard accessible
- Section provides logical navigation target
- Backlink provides easy return path

### Sighted Users
- Image visible in extended description for reference
- Clear "Return to content" link
- Natural reading flow maintained

### All Users
- Descriptions don't clutter main content
- Available on-demand
- Proper bidirectional navigation
- EPUB 3 and WCAG compliant

## Standards Compliance

This pattern follows:

- ✅ **WCAG 2.1** - Success Criterion 1.1.1 (Non-text Content)
- ✅ **EPUB Accessibility 1.1** - Extended descriptions guidance
- ✅ **ARIA 1.2** - aria-details attribute usage
- ✅ **DPUB-ARIA 1.0** - doc-backlink role
- ✅ **HTML5** - Section element semantics

## Testing Recommendations

### With Screen Readers

**NVDA (Windows):**
- Image should announce "has extended description"
- Insert+Ctrl+D navigates to description
- Backlink announces as "backlink"

**JAWS (Windows):**
- Image announces extended description availability
- Can list images with descriptions
- Recognizes doc-backlink role

**VoiceOver (macOS/iOS):**
- Rotor can list images with descriptions
- Can navigate to linked description
- Announces backlink clearly

### With Validators

**EPUBCheck:**
- Validates EPUB 3 structure
- Checks XHTML validity
- Verifies link integrity

**Ace by DAISY:**
- Checks accessibility features
- Validates ARIA usage
- Reports on extended descriptions

## Common Issues and Solutions

### Issue: Screen reader doesn't announce extended description
**Solution:** Check that `aria-details` points to the link's ID, not the section ID

### Issue: Image announced twice
**Solution:** Verify image in extended description has both `role="presentation"` AND `alt=""`

### Issue: Backlink not recognized
**Solution:** Ensure `role="doc-backlink"` is on the anchor element, not the paragraph

### Issue: Link doesn't work
**Solution:** Verify section ID matches the fragment in the link's href exactly

## Further Reading

- [WCAG Extended Descriptions](https://www.w3.org/WAI/WCAG21/Techniques/general/G73)
- [ARIA aria-details](https://www.w3.org/TR/wai-aria-1.2/#aria-details)
- [EPUB Accessibility 1.1](https://www.w3.org/TR/epub-a11y-11/)
- [DPUB-ARIA doc-backlink](https://www.w3.org/TR/dpub-aria-1.0/#doc-backlink)
- [DAISY Knowledge Base](http://kb.daisy.org/publishing/docs/html/images.html)
