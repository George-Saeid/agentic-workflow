"""
Google Sheet Structure Extractor (Pattern-Aware)
Extracts only the structure with pattern recognition - no data values.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for Google Sheets API (read-only)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extract spreadsheet ID from URL or return if already an ID."""
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url_or_id)
    return match.group(1) if match else url_or_id.strip()

def get_google_sheets_service():
    """Authenticate and return Google Sheets API service."""
    creds = None
    project_root = Path(__file__).parent.parent
    token_path = project_root / 'token.json'
    credentials_path = project_root / 'credentials.json'
    
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {credentials_path}\n"
            "Please download OAuth credentials from Google Cloud Console"
        )
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    
    return build('sheets', 'v4', credentials=creds)

def is_date(value: str) -> bool:
    """Check if string looks like a date."""
    if not value:
        return False
    # Common date patterns
    date_patterns = [
        r'^\d{1,2}/\d{1,2}/\d{4}$',  # 26/09/2025
        r'^\d{4}-\d{2}-\d{2}$',      # 2025-09-26
        r'^\d{1,2}-\d{1,2}-\d{4}$',  # 26-09-2025
    ]
    return any(re.match(pattern, str(value)) for pattern in date_patterns)

def detect_pattern(values: List[str]) -> Dict:
    """
    Detect repeating patterns in a list of values.
    
    Returns:
        Dictionary describing the pattern
    """
    if not values:
        return {"type": "empty"}
    
    # Filter out None/empty values for analysis
    non_empty = [v for v in values if v]
    
    if len(non_empty) == 0:
        return {"type": "all_empty", "count": len(values)}
    
    if len(non_empty) == 1:
        return {"type": "single", "value": non_empty[0]}
    
    # Check if all identical
    if len(set(non_empty)) == 1:
        return {"type": "uniform", "value": non_empty[0], "count": len(values)}
    
    # Try to detect repeating blocks
    for block_size in range(1, min(11, len(non_empty) // 2 + 1)):
        blocks = []
        for i in range(0, len(non_empty), block_size):
            block = non_empty[i:i+block_size]
            if len(block) == block_size:
                blocks.append(block)
        
        # Need at least 2 complete blocks
        if len(blocks) < 2:
            continue
            
        # Create template from first block
        template = []
        for val in blocks[0]:
            if is_date(val):
                template.append("<date>")
            elif val and str(val).replace('.', '').replace('-', '').isdigit():
                template.append("<number>")
            else:
                template.append(val)
        
        # Check if other blocks match template
        matching_blocks = 1  # First block always matches
        breaks = []
        
        for idx, block in enumerate(blocks[1:], start=1):
            block_template = []
            for val in block:
                if is_date(val):
                    block_template.append("<date>")
                elif val and str(val).replace('.', '').replace('-', '').isdigit():
                    block_template.append("<number>")
                else:
                    block_template.append(val)
            
            if block_template == template:
                matching_blocks += 1
            else:
                breaks.append({
                    "block_index": idx,
                    "position": idx * block_size,
                    "expected_template": template,
                    "actual_values": block
                })
        
        # If most blocks match (>70%), we found a pattern
        if matching_blocks >= len(blocks) * 0.7:
            result = {
                "type": "repeating",
                "block_size": block_size,
                "template": template,
                "repeat_count": len(blocks),
                "total_items": len(non_empty),
                "sample_first_block": blocks[0]
            }
            
            if breaks:
                result["breaks"] = breaks
            
            return result
    
    # No repeating pattern - check for sequences (dates, numbers)
    if len(non_empty) >= 3:
        # Check if mostly dates
        date_count = sum(1 for v in non_empty if is_date(v))
        if date_count > len(non_empty) * 0.7:
            return {
                "type": "date_sequence",
                "count": len(non_empty),
                "first": non_empty[0],
                "last": non_empty[-1],
                "sample": non_empty[:5]
            }
    
    # Check for common prefixes
    if len(non_empty) > 5:
        # Group by common prefixes
        prefixes = {}
        for val in non_empty:
            prefix = str(val).split()[0] if ' ' in str(val) else str(val)[:min(5, len(str(val)))]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        dominant = max(prefixes.items(), key=lambda x: x[1]) if prefixes else None
        if dominant and dominant[1] > len(non_empty) * 0.3:
            return {
                "type": "varied_with_prefix",
                "common_prefix": dominant[0],
                "prefix_count": dominant[1],
                "total": len(non_empty),
                "sample": non_empty[:5]
            }
    
    # No pattern - just list unique values if reasonable
    unique = list(dict.fromkeys(non_empty))  # Preserve order
    if len(unique) <= 20:
        return {
            "type": "list",
            "values": unique,
            "total": len(values)
        }
    else:
        return {
            "type": "varied",
            "unique_count": len(unique),
            "total": len(values),
            "sample": non_empty[:10]
        }

def extract_sheet_structure(service, spreadsheet_id: str, sheet_name: str) -> Dict:
    """
    Extract structure of a single sheet (headers only, no data).
    """
    try:
        # Get sheet dimensions first
        metadata = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[sheet_name],
            includeGridData=False
        ).execute()
        
        sheets = metadata.get('sheets', [])
        dimensions = {"rows": 0, "columns": 0}
        frozen_rows = 0
        frozen_cols = 0
        
        if sheets:
            grid_props = sheets[0].get('properties', {}).get('gridProperties', {})
            dimensions = {
                "rows": grid_props.get('rowCount', 0),
                "columns": grid_props.get('columnCount', 0)
            }
            frozen_rows = grid_props.get('frozenRowCount', 0)
            frozen_cols = grid_props.get('frozenColumnCount', 0)
        
        if dimensions['rows'] == 0:
            return {
                "sheet_name": sheet_name,
                "is_empty": True
            }
        
        # Get just header rows (first ~20 rows to detect row headers)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1:ZZZ20",
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return {
                "sheet_name": sheet_name,
                "is_empty": True
            }
        
        # Extract column headers (first row)
        column_headers = values[0] if values else []
        
        # Extract row headers (first column of first ~20 rows)
        row_headers = [row[0] if row else None for row in values]
        
        # Detect patterns
        col_pattern = detect_pattern(column_headers)
        row_pattern = detect_pattern(row_headers)
        
        result = {
            "sheet_name": sheet_name,
            "is_empty": False,
            "dimensions": dimensions,
            "column_structure": col_pattern,
            "row_structure": row_pattern
        }
        
        # Add frozen info if present
        if frozen_rows or frozen_cols:
            result["frozen"] = {
                "rows": frozen_rows,
                "columns": frozen_cols
            }
        
        return result
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}", file=sys.stderr)
        return {
            "sheet_name": sheet_name,
            "error": str(e)
        }

def extract_spreadsheet_structure(url_or_id: str) -> Dict:
    """
    Extract structure of entire spreadsheet with pattern recognition.
    """
    try:
        spreadsheet_id = extract_spreadsheet_id(url_or_id)
        service = get_google_sheets_service()
        
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        title = spreadsheet.get('properties', {}).get('title', 'Unknown')
        locale = spreadsheet.get('properties', {}).get('locale', 'unknown')
        timezone = spreadsheet.get('properties', {}).get('timeZone', 'unknown')
        
        # Get all sheets
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        # Extract structure from each sheet
        sheets_structure = []
        for sheet_name in sheet_names:
            print(f"Analyzing: {sheet_name}...", file=sys.stderr)
            structure = extract_sheet_structure(service, spreadsheet_id, sheet_name)
            sheets_structure.append(structure)
        
        result = {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            "title": title,
            "locale": locale,
            "timezone": timezone,
            "sheet_count": len(sheets),
            "sheets": sheets_structure
        }
        
        return {"status": "success", "data": result}
        
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except HttpError as error:
        return {"status": "error", "message": f"Google API error: {error}"}
    except Exception as error:
        return {"status": "error", "message": f"Unexpected error: {error}"}

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_sheet_structure.py <spreadsheet_url_or_id>")
        sys.exit(1)
    
    url_or_id = sys.argv[1]
    
    print(f"Extracting sheet structure...", file=sys.stderr)
    result = extract_spreadsheet_structure(url_or_id)
    
    if result['status'] == 'success':
        data = result['data']
        spreadsheet_id = data['spreadsheet_id']
        
        # Save to .tmp directory
        tmp_dir = Path(__file__).parent.parent / '.tmp'
        tmp_dir.mkdir(exist_ok=True)
        
        output_file = tmp_dir / f"sheet_structure_{spreadsheet_id}.json"
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        
        print(f"\n✓ Structure extraction complete!", file=sys.stderr)
        print(f"  Spreadsheet: {data['title']}", file=sys.stderr)
        print(f"  Sheets: {data['sheet_count']}", file=sys.stderr)
        print(f"  Output: {output_file}", file=sys.stderr)
        
        sys.exit(0)
    else:
        print(f"\n✗ Error: {result['message']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
