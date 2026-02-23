# Analyze Google Sheet

## Goal
Extract data from a Google Sheet in an LLM-friendly tabular format for easy understanding and querying.

## Inputs
- `sheet_url` (string): Full Google Sheets URL
  - Format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit...`
  - Can also accept just the spreadsheet ID
- `max_rows` (int, optional): Maximum rows to extract per sheet (default: 5000)

## Tools/Scripts
- `execution/extract_sheet_data.py`: Main script that extracts actual data in tabular format
- `execution/analyze_sheet_structure.py`: (Legacy) Detailed structural analysis - only use if you need formula/validation metadata

## Outputs
- JSON file saved to `.tmp/sheet_data_{spreadsheet_id}.json` containing:
  - **Spreadsheet metadata**: title, ID, URL, locale, timezone
  - **List of sheets** with:
    - Sheet name
    - Dimensions (row/column count)
    - **Headers**: List of column names
    - **Data**: Array of row objects (each row is a dict with header:value pairs)
  - **Summary**: Total sheets, sheet names, total data rows
  
**Format Example:**
```json
{
  "sheets": [
    {
      "sheet_name": "جدول",
      "dimensions": {"rows": 75, "columns": 209},
      "headers": ["الخدمة", "26/09/2025", "العدد", ...],
      "data": [
        {"الخدمة": "مذبح باكر", "26/09/2025": "انجيلوس عماد", "العدد": "1", ...},
        {"الخدمة": "الشورية", "26/09/2025": "يوحنا بيتر", "العدد": "2", ...}
      ]
    }
  ]
}
```

## Process
1. AI orchestrator receives Google Sheets URL from user
2. Extracts spreadsheet ID from URL
3. Calls `execution/extract_sheet_data.py` with the ID and optional row limit
4. Script authenticates with Google Sheets API
5. Fetches spreadsheet metadata and all sheet data using `FORMATTED_VALUE` render option
6. Converts each sheet into tabular format:
   - First row becomes column headers (with uniqueness guarantee)
   - Remaining rows become data objects with header:value mapping
7. Saves complete data to `.tmp/` directory
8. Returns summary to AI orchestrator
9. AI reports findings and can answer data queries directly

## Edge Cases
- **Invalid URL/ID**: Validate format before API call
- **No access/permissions**: Handle authentication errors gracefully
- **Empty sheets**: Report as empty with empty data array
- **Multiple sheets**: Extract all sheets in the spreadsheet
- **Large sheets**: Default limit of 5000 rows per sheet (configurable)
- **Duplicate headers**: Automatically append `_1`, `_2`, etc. to ensure uniqueness
- **No headers**: First row is always treated as headers
- **Empty cells**: Represented as `null` in the data objects
- **Ragged rows**: Rows padded with `null` to match header length

## Authentication
Requires Google OAuth credentials:
- `credentials.json` file in project root
- Will generate `token.json` on first run
- Needs Google Sheets API enabled in Google Cloud Console

## Notes
- **Read-only**: No modifications to sheets
- **LLM-optimized**: Flat, tabular structure for easy querying
- **Actual data**: Contains real cell values, not just metadata
- **Fast extraction**: Uses `values().get()` API which is faster than full metadata fetch
- **Formatted values**: Dates appear as "26/09/2025" not serial numbers
- Intermediate results cached in `.tmp/` for reuse
- For structural analysis (formulas, dropdowns, cell types), use `analyze_sheet_structure.py` instead
