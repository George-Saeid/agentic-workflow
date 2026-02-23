# Extract Google Sheet Structure

## Goal
Extract Google Sheet structure in the most compact, pattern-aware format for LLM understanding - no data values, just the structural layout with pattern recognition.

## Inputs
- `sheet_url` (string): Full Google Sheets URL
  - Format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit...`
  - Can also accept just the spreadsheet ID

## Tools/Scripts
- `execution/extract_sheet_structure.py`: **DEFAULT** - Pattern-aware structure extraction (structure only, no data)
- `execution/extract_sheet_data.py`: Use when you need actual cell values for data analysis
- `execution/analyze_sheet_structure.py`: (Legacy) Use only if you need formula/validation metadata

## Outputs
- JSON file saved to `.tmp/sheet_structure_{spreadsheet_id}.json` containing:
  - **Spreadsheet metadata**: title, ID, URL, locale, timezone
  - **List of sheets** with:
    - Sheet name
    - Dimensions (row/column count)
    - **Column structure**: Pattern detected in column headers
    - **Row structure**: Pattern detected in row headers
    - Frozen rows/columns (if any)
  
**Pattern Types:**
- `repeating`: Detected repeating block pattern (e.g., `[<date>, "العدد", "غياب"] x 52`)
- `uniform`: All values identical
- `date_sequence`: Series of dates
- `list`: Small list of unique values (≤20 items)
- `varied_with_prefix`: Many values with common prefix
- `varied`: No clear pattern, shows sample

**Format Example:**
```json
{
  "sheets": [
    {
      "sheet_name": "جدول",
      "dimensions": {"rows": 78, "columns": 209},
      "column_structure": {
        "type": "repeating",
        "block_size": 4,
        "template": ["<date>", "العدد", "غياب", "تقييم"],
        "repeat_count": 52,
        "breaks": []
      },
      "row_structure": {
        "type": "list",
        "values": ["الخدمة", "مذبح باكر 1", "الشورية", ...]
      },
      "frozen": {"rows": 1, "columns": 1}
    }
  ]
}
```

**When Pattern Breaks:**
```json
{
  "type": "repeating",
  "template": ["<date>", "count"],
  "breaks": [
    {
      "block_index": 15,
      "position": 30,
      "expected_template": ["<date>", "count"],
      "actual_values": ["<date>", "total", "summary"]
    }
  ]
}
```

## Process
1. AI orchestrator receives Google Sheets URL from user
2. Extracts spreadsheet ID from URL
3. Calls `execution/extract_sheet_structure.py` with the ID
4. Script authenticates with Google Sheets API
5. For each sheet:
   - Fetches metadata (dimensions, frozen rows/columns)
   - Fetches first 20 rows using `FORMATTED_VALUE` render option
   - Extracts column headers (row 1) and row headers (column A)
   - Applies pattern detection algorithm:
     - Tests block sizes 1-10 for repeating patterns
     - Creates templates replacing dates with `<date>`, numbers with `<number>`
     - Detects pattern breaks and where they resume
     - Falls back to prefix analysis or sampling if no pattern found
6. Saves ultra-compact structure to `.tmp/` directory
7. Returns summary to AI orchestrator
8. AI can understand sheet layout from patterns alone

## Edge Cases
- **Invalid URL/ID**: Validate format before API call
- **No access/permissions**: Handle authentication errors gracefully
- **Empty sheets**: Report as empty
- **Multiple sheets**: Extract all sheets in the spreadsheet
- **Irregular patterns**: Falls back to sampling (shows first 10 values)
- **Pattern breaks**: Recorded with position and expected vs actual values
- **Mixed content**: Template uses placeholders like `<date>`, `<number>` for varying data
- **No pattern found**: Shows sample + unique count for understanding

## Authentication
Requires Google OAuth credentials:
- `credentials.json` file in project root
- Will generate `token.json` on first run
- Needs Google Sheets API enabled in Google Cloud Console

## Notes
- **Structure only**: No data values extracted (privacy-friendly, fast)
- **Pattern recognition**: Compresses 100+ columns into 1 template
- **Ultra-compact**: 99.5% smaller than full analysis (11KB vs 2.2MB)
- **LLM-optimized**: AI can understand structure without seeing all data
- **Fast extraction**: Only reads first 20 rows per sheet
- **Break detection**: Identifies where patterns change or are interrupted
- Results cached in `.tmp/` for reuse
- For actual data extraction, use `extract_sheet_data.py` instead
- For formula/validation analysis, use `analyze_sheet_structure.py` instead
