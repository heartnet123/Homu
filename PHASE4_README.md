# Phase 4: Enhanced UI & UX

## Overview
Phase 4 transforms the interface into a professional legal tool with document viewing, clickable citations, and export capabilities for legal professionals.

## Features

### 1. Document Viewer (`DocumentViewer`)
- **Modal-based PDF viewer** with iframe rendering
- **Page navigation**: Previous/Next buttons + direct page input
- **Zoom controls**: 50% - 200% zoom levels
- **Rotate function**: 90-degree rotation
- **Highlight tracking**: Shows which citation triggered the view
- **Fullscreen modal**: Takes up 90% of viewport

```tsx
<DocumentViewer
  documentUrl="/api/documents/123/view"
  documentName="พรบ.แรงงาน.pdf"
  pageNumber={15}
  highlightText="มาตรา 12"
  isOpen={true}
  onClose={() => setIsOpen(false)}
/>
```

### 2. Citation Links (`CitationLink`, `CitedText`)
- **Automatic citation parsing** from LLM responses
- **Clickable badges** that open document viewer at specific pages
- **Color-coded by type**:
  - Blue: มาตรา (Sections)
  - Green: ข้อ (Articles)
  - Purple: Collections
- **Pattern matching** supports:
  - `[Collection: X] [Doc: Y] [Page: N] [มาตรา Z]`
  - `[Page: N] [มาตรา Z]`
  - `มาตรา Z (Page: N)`
  - `มาตรา Z`

### 3. Export Functionality
- **PDF Export**: Using ReportLab with Thai font support
- **Word Export**: Using python-docx
- **Includes**:
  - All Q&A pairs with timestamps
  - Full citations formatted in Thai
  - Collection and search strategy metadata
  - Professional legal document formatting

#### API Endpoint
```
POST /api/export
{
  "messages": [...],
  "format": "pdf" | "docx",
  "title": "Legal Consultation Report",
  "collectionName": "แรงงาน",
  "searchStrategy": "hybrid"
}
```

### 4. Collection Card Grid (`CollectionCard`, `CollectionGrid`)
- **Card-based browsing** with hover effects
- **Category color coding**:
  - แรงงาน: Blue
  - ภาษี: Green
  - ลิขสิทธิ์: Purple
  - อาญา: Red
  - แพ่ง: Yellow
  - บริษัท: Indigo
  - ทั่วไป: Gray
- **Document count** and **last updated** displayed
- **Responsive grid**: 1-3 columns based on screen size

### 5. Document View API
```
GET /api/documents/{document_id}/view
```
- Returns file with proper content-type
- Inline disposition for browser viewing
- Supports PDF and DOCX

## Files Added/Modified

### New Components
| File | Description |
|------|-------------|
| `frontend/components/document-viewer.tsx` | PDF viewer with navigation |
| `frontend/components/citation-link.tsx` | Clickable citation badges |
| `frontend/components/collection-card.tsx` | Collection browser cards |
| `backend/export_service.py` | PDF/Word export service |

### Modified Files
| File | Changes |
|------|---------|
| `backend/main.py` | Added `/api/export` and `/api/documents/{id}/view` endpoints |
| `backend/requirements.txt` | Added `reportlab`, `python-docx` |
| `frontend/app/page.tsx` | Added export button, document map integration |

## Usage

### Viewing Source Documents
1. Ask a legal question
2. AI responds with citations like `[Page: 15] [มาตรา 12]`
3. Click citation badge
4. Document viewer opens at page 15

### Exporting Chat History
1. Have at least one Q&A exchange
2. Click download (↓) button in header
3. PDF downloads automatically with:
   - Title: "Legal Consultation - {Collection Name}"
   - Date and metadata
   - All questions and answers
   - Citation list per answer

### Browsing Collections
Use `CollectionGrid` component:
```tsx
<CollectionGrid
  collections={collections}
  selectedId={currentCollectionId}
  onSelect={(c) => setCurrentCollectionId(c.id)}
  onViewDocuments={(c) => showDocuments(c.id)}
/>
```

## UI Flow

```
User asks question
       ↓
AI responds with citations [Page: 15] [มาตรา 12]
       ↓
User clicks citation badge
       ↓
DocumentViewer opens with PDF at page 15
       ↓
User can zoom, rotate, navigate pages
       ↓
User clicks Export (↓) button
       ↓
PDF/Word downloads with full Q&A + citations
```

## Technical Notes

### Thai Font Support (PDF)
The export service attempts to use THSarabun font for Thai text. If not available, falls back to Helvetica.

### Document URL Mapping
Frontend needs to maintain a `documentMap` to resolve citation document names to URLs:
```tsx
const documentMap = {
  "พรบ.แรงงาน.pdf": {
    url: "/api/documents/123/view",
    name: "พรบ.แรงงาน.pdf"
  }
};
```

### Export Limitations
- PDF: Best for sharing/printing
- Word: Best for editing/further work
- Both formats include all citations and metadata

## Next Steps (Future Enhancements)

1. **Side-by-side mode**: Split screen with chat and document
2. **Multiple document tabs**: View several sources simultaneously
3. **Annotation tools**: Highlight and add notes to PDFs
4. **Search within document**: Full-text search inside PDF viewer
5. **Citation verification**: Cross-check citations against actual text
