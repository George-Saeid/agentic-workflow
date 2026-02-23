# Analyze Google Sheet Structure

## Goal
Extract and analyze the complete structure of a Google Sheet including columns, rows, headers, data types, and metadata.

## Inputs
- `sheet_url` (string): Full Google Sheets URL
  - Format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit...`
  - Can also accept just the spreadsheet ID

## Tools/Scripts
- `execution/analyze_sheet_structure.py`: Main script that connects to Google Sheets API and extracts structure

## Outputs
- JSON file saved to `.tmp/sheet_analysis_{spreadsheet_id}.json` containing:
  - Spreadsheet metadata (title, ID, locale)
  - List of all sheets/tabs in the spreadsheet
  - For each sheet:
    - Sheet name and ID
    - Dimensions (row count, column count)
    - Column headers (first row analysis)
    - Row headers (first column analysis)
    - Cell type analysis for each column:
      - **Formulas**: Detect and record formula content
        - Formula ranges (where formulas start and end)
        - Formula patterns (normalized to detect similar formulas)
        - Formula flow (how formulas extend, where they break, where they continue)
        - Break detection (non-formula cells interrupting formula sequences)
      - **Dropdowns**: Detect data validation (dropdown lists with options)
      - **Checkboxes**: Detect checkbox cells
      - **Plain text/numbers**: Regular data cells
    - Data type distribution (text, number, date, URL, email, boolean)
    - Frozen rows/columns
    - Protected ranges (if any)

## Process
1. AI orchestrator receives Google Sheets URL from user
2. Extracts spreadsheet ID from URL
3. Calls `execution/analyze_sheet_structure.py` with the ID
4. Script authenticates with Google Sheets API
5. Fetches spreadsheet metadata and all sheet data
6. Analyzes structure, headers, data types
7. Saves analysis to `.tmp/` directory
8. Returns summary to AI orchestrator
9. AI reports findings to user

## Edge Cases
- **Invalid URL/ID**: Validate format before API call
- **No access/permissions**: Handle authentication errors gracefully
- **Empty sheets**: Report as empty, don't error
- **Multiple sheets**: Analyze all sheets in the spreadsheet
- **Large sheets**: Consider sampling for sheets with >10,000 rows
- **Mixed data types**: Report dominant type and percentage breakdown
- **No headers**: Assume first row/column might be headers, but flag confidence
- **Protected sheets**: Note permissions but still analyze structure if readable

## Authentication
Requires Google OAuth credentials:
- `credentials.json` file in project root
- Will generate `token.json` on first run
- Needs Google Sheets API enabled in Google Cloud Console

## Notes
- This is read-only analysis - no modifications to sheets
- Intermediate results cached in `.tmp/` for performance
- Can be used as foundation for other sheet operations
- Consider rate limits for very large spreadsheets
