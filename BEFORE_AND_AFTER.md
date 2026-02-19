# Before and After Example
## process-epub-ext-descs

This document shows a complete before/after transformation demonstrating the accessibility pattern implementation.

---

## BEFORE Processing

### Input XHTML (chapter01.xhtml)

```html
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Chapter 1: Understanding Complex Diagrams</title>
</head>
<body>
  <h1>Chapter 1: Understanding Complex Diagrams</h1>
  
  <p>This chapter explores how we can make complex diagrams more accessible.</p>
  
  <div class="figure">
    <img src="images/diagram.jpg" alt="Flow diagram showing the water cycle"/>
    <p>Figure 1: The Water Cycle</p>
  </div>
  
  <p>Beginning of extended description.</p>
  <p>This diagram illustrates the complete water cycle in Earth's hydrosphere. 
     The process begins with evaporation from bodies of water, shown in the 
     lower left portion of the diagram.</p>
  <p>Key components include:</p>
  <ul>
    <li><strong>Evaporation</strong>: Water vapor rises from oceans and lakes</li>
    <li><strong>Condensation</strong>: Water vapor forms clouds in the upper atmosphere</li>
    <li><strong>Precipitation</strong>: Rain and snow fall back to Earth's surface</li>
    <li><strong>Collection</strong>: Water accumulates in rivers, lakes, and oceans</li>
  </ul>
  <p>The diagram also shows groundwater flow beneath the surface, represented by 
     dotted lines, and the effect of solar energy, depicted by a yellow sun symbol 
     in the upper right corner.</p>
  <p>End of extended description.</p>
  
  <p>As we can see from this diagram, the water cycle is a continuous process.</p>
</body>
</html>
```

---

## AFTER Processing

### Modified Original File (chapter01.xhtml)

```html
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Chapter 1: Understanding Complex Diagrams</title>
</head>
<body>
  <h1>Chapter 1: Understanding Complex Diagrams</h1>
  
  <p>This chapter explores how we can make complex diagrams more accessible.</p>
  
  <div class="figure">
    <!-- Image now has ID and aria-details attribute -->
    <img src="images/diagram.jpg" 
         alt="Flow diagram showing the water cycle" 
         id="diagram-001" 
         aria-details="anchor-extended-description-diagram-001"/>
    <p>Figure 1: The Water Cycle</p>
  </div>
  
  <!-- Delimiters and description content replaced with link -->
  <p>
    <a id="anchor-extended-description-diagram-001" 
       href="desc-diagram-001.xhtml#extended-description-diagram-001">
      Extended description
    </a>
  </p>
  
  <p>As we can see from this diagram, the water cycle is a continuous process.</p>
</body>
</html>
```

### New Extended Description File (desc-diagram-001.xhtml)

```html
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
    <title>Extended Description</title>
  </head>
  <body>
    <!-- Section wrapper with ID matching link's href fragment -->
    <section id="extended-description-diagram-001">
      
      <!-- Presentational image for visual reference -->
      <img role="presentation" 
           alt="" 
           src="images/diagram.jpg"/>
      
      <!-- Extended description content (extracted from original) -->
      <p>
        This diagram illustrates the complete water cycle in Earth's hydrosphere. 
        The process begins with evaporation from bodies of water, shown in the 
        lower left portion of the diagram.
      </p>
      
      <p>Key components include:</p>
      <ul>
        <li><strong>Evaporation</strong>: Water vapor rises from oceans and lakes</li>
        <li><strong>Condensation</strong>: Water vapor forms clouds in the upper atmosphere</li>
        <li><strong>Precipitation</strong>: Rain and snow fall back to Earth's surface</li>
        <li><strong>Collection</strong>: Water accumulates in rivers, lakes, and oceans</li>
      </ul>
      
      <p>
        The diagram also shows groundwater flow beneath the surface, represented by 
        dotted lines, and the effect of solar energy, depicted by a yellow sun symbol 
        in the upper right corner.
      </p>
      
      <!-- Backlink with doc-backlink role -->
      <p>
        <a role="doc-backlink" href="chapter01.xhtml#diagram-001">
          Return to content
        </a>
      </p>
      
    </section>
  </body>
</html>
```

---

## Key Changes Explained

### 1. Image Gets Accessibility Attributes

**Before:**
```html
<img src="images/diagram.jpg" alt="Flow diagram showing the water cycle"/>
```

**After:**
```html
<img src="images/diagram.jpg" 
     alt="Flow diagram showing the water cycle" 
     id="diagram-001" 
     aria-details="anchor-extended-description-diagram-001"/>
```

**What changed:**
- Added `id="diagram-001"` for backlinking
- Added `aria-details` pointing to the link's ID
- Screen readers now announce "extended description available"

### 2. Description Content Becomes Link

**Before:**
```html
<p>Beginning of extended description.</p>
<p>This diagram illustrates...</p>
<ul>...</ul>
<p>End of extended description.</p>
```

**After:**
```html
<p>
  <a id="anchor-extended-description-diagram-001" 
     href="desc-diagram-001.xhtml#extended-description-diagram-001">
    Extended description
  </a>
</p>
```

**What changed:**
- Delimiters removed
- Content moved to separate file
- Replaced with accessible link
- Link has ID matching `aria-details` reference

### 3. New File Created with Proper Structure

**New file:** `desc-diagram-001.xhtml`

**Structure:**
- Section wrapper with fragment ID
- Presentational image copy
- All description content preserved
- Backlink for return navigation

### 4. Updated Package Document

**Before (content.opf manifest):**
```xml
<manifest>
  <item id="chapter01" href="chapter01.xhtml" media-type="application/xhtml+xml"/>
  <item id="img001" href="images/diagram.jpg" media-type="image/jpeg"/>
</manifest>
```

**After (content.opf manifest):**
```xml
<manifest>
  <item id="chapter01" href="chapter01.xhtml" media-type="application/xhtml+xml"/>
  <item id="img001" href="images/diagram.jpg" media-type="image/jpeg"/>
  <item id="desc-002" href="desc-diagram-001.xhtml" media-type="application/xhtml+xml"/>
</manifest>
```

**What changed:**
- New item added to manifest
- Not added to spine (not in linear reading order)

---

## Accessibility Benefits

### For Screen Reader Users

**Before:**
- Long description interrupts main content flow
- No way to skip if already familiar with diagram
- Description might be read out of context

**After:**
- Image announces "has extended description"
- Can choose to access or skip description
- Can jump directly to description with keyboard shortcut
- Backlink clearly marked for return navigation

### For Keyboard Users

**Before:**
- Must tab through entire description to continue
- No shortcut to access description

**After:**
- Link is keyboard accessible
- Can choose to follow or skip
- Easy return with backlink

### For All Users

**Before:**
- Extended descriptions clutter main text
- Makes content harder to read
- Can't be easily referenced separately

**After:**
- Clean, uncluttered main content
- Descriptions available on-demand
- Can be bookmarked or linked to directly
- Better organization and navigation

---

## Testing the Output

### Screen Reader Test Points

1. **Navigate to image:**
   - Should announce "Flow diagram showing the water cycle, has extended description"
   
2. **Access description:**
   - Screen reader shortcut (e.g., NVDA: Insert+Ctrl+D) should jump to description
   
3. **In description file:**
   - Image should be silent (role="presentation")
   - Content should read naturally
   
4. **Backlink:**
   - Should announce as "backlink"
   - Should return to original image location

### Visual Test Points

1. **Main content:**
   - Image displays normally
   - Link to extended description visible and clickable
   
2. **Extended description:**
   - Image shows for visual reference
   - Description content formatted properly
   - Backlink clearly visible

### Validation Test Points

```bash
# Run EPUB validation
python test_epub.py desc-diagram-001.xhtml

# Check for:
# ✓ Valid EPUB structure
# ✓ Section wrapper present
# ✓ Presentational image (role="presentation", alt="")
# ✓ Backlink with role="doc-backlink"
# ✓ Valid XHTML
```

---

## Summary

The transformation creates a WCAG-compliant, EPUB Accessibility 1.1-compliant structure that:

✅ Keeps main content clean and readable  
✅ Makes descriptions accessible on-demand  
✅ Provides proper semantic structure  
✅ Supports screen reader navigation  
✅ Enables bidirectional linking  
✅ Prevents duplicate announcements  
✅ Follows best practices for accessible publishing  
