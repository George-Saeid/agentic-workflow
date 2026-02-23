# Extract PDF Data with Docling

## Goal
Extract text, tables, images, and document structure from PDF files using IBM's Docling library.

## Inputs
- `pdf_path` (string): Path to the PDF file (absolute or relative to project root)
- `output_format` (string, optional): Output format - "markdown", "json", "text", or "all" (default: "json")
- `extract_images` (boolean, optional): Whether to extract and save images (default: True)
- `extract_tables` (boolean, optional): Whether to extract tables separately (default: True)

## Tools/Scripts
- `execution/extract_pdf_docling.py`: Main script for PDF extraction using Docling

## Outputs
- JSON file saved to `.tmp/pdf_extract_{filename}_{timestamp}.json` containing:
  - **Document metadata**: title, page count, file size
  - **Text content**: Extracted text from all pages
  - **Tables**: Structured table data (if `extract_tables=True`)
  - **Images**: List of extracted images with paths (if `extract_images=True`)
  - **Document structure**: Headings, paragraphs, lists hierarchy
  - **Page-by-page breakdown**: Content organized by page number

- Optional additional outputs:
  - `.tmp/pdf_extract_{filename}.md`: Markdown version (if `output_format="markdown"` or `"all"`)
  - `.tmp/pdf_extract_{filename}.txt`: Plain text version (if `output_format="text"` or `"all"`)
  - `.tmp/pdf_images_{filename}/`: Directory with extracted images (if `extract_images=True`)

**Format Example:**
```json
{
  "metadata": {
    "filename": "report.pdf",
    "page_count": 25,
    "file_size_bytes": 2458624,
    "extraction_date": "2026-02-23T14:30:22",
    "docling_version": "1.0.0"
  },
  "document_structure": {
    "title": "Annual Report 2025",
    "sections": [
      {
        "heading": "Executive Summary",
        "level": 1,
        "page": 1,
        "content": "..."
      }
    ]
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Full page text...",
      "tables": [...],
      "images": [...]
    }
  ],
  "tables": [
    {
      "page": 3,
      "table_index": 1,
      "headers": ["Q1", "Q2", "Q3", "Q4"],
      "rows": [...]
    }
  ],
  "images": [
    {
      "page": 2,
      "image_index": 1,
      "path": ".tmp/pdf_images_report/page_2_img_1.png",
      "width": 800,
      "height": 600
    }
  ]
}
```

## Process
1. AI orchestrator receives PDF file path from user
2. Validates that the file exists and is a PDF
3. Calls `execution/extract_pdf_docling.py` with parameters
4. Script processes PDF using Docling:
   - Loads PDF document
   - Extracts text with layout preservation
   - Identifies and extracts tables with structure
   - Extracts images and saves them
   - Identifies document structure (headings, paragraphs, lists)
   - Organizes content by page
5. Saves structured output to `.tmp/` directory
6. Returns summary to AI orchestrator with key statistics

## Edge Cases
- **File not found**: Validate path exists before processing
- **Invalid PDF**: Check file format and handle corrupted files gracefully
- **Password-protected PDFs**: Report that password protection is detected (future enhancement)
- **Large PDFs**: Process in chunks if memory issues occur, provide progress updates
- **Scanned PDFs**: Docling handles OCR automatically, but quality may vary
- **Complex layouts**: Two-column layouts, text boxes - Docling attempts to maintain reading order
- **No extractable content**: Report empty or image-only PDFs
- **Unsupported PDF versions**: Handle gracefully with error message
- **Special characters/encodings**: Preserve UTF-8 encoding throughout
- **Embedded fonts**: Handle PDFs with non-standard fonts

## Notes
- **Docling** is IBM's state-of-the-art document understanding library
- Handles both digital and scanned PDFs (OCR built-in)
- Better table extraction than traditional libraries (pypdf, pdfplumber)
- Maintains document structure and hierarchy
- First run may download ML models (~200MB)
- Intermediate files in `.tmp/` can be regenerated, final insights should be in deliverables

## Installation
Add to `requirements.txt`:
```
docling>=1.0.0
```

Run: `pip install docling`
