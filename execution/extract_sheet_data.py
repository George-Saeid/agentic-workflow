"""
Google Sheet Data Extractor
Extracts actual data from Google Sheets in an LLM-friendly tabular format.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

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

def get_cell_value(cell: Dict) -> Any:
    """Extract the formatted or effective value from a cell."""
    # Priority: formattedValue > effectiveValue
    if 'formattedValue' in cell:
        return cell['formattedValue']
    
    if 'effectiveValue' in cell:
        effective = cell['effectiveValue']
        if 'stringValue' in effective:
            return effective['stringValue']
        elif 'numberValue' in effective:
            return effective['numberValue']
        elif 'boolValue' in effective:
            return effective['boolValue']
    
    return None

def extract_sheet_data(service, spreadsheet_id: str, sheet_name: str, max_rows: int = 5000) -> Dict:
    """
    Extract data from a single sheet in tabular format.
    
    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to extract
        max_rows: Maximum number of rows to fetch
        
    Returns:
        Dictionary with sheet data in tabular format
    """
    try:
        # First, get sheet properties
        metadata = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[sheet_name],
            includeGridData=False
        ).execute()
        
        sheets = metadata.get('sheets', [])
        if not sheets:
            return {
                'sheet_name': sheet_name,
                'is_empty': True,
                'rows': []
            }
        
        properties = sheets[0].get('properties', {})
        grid_props = properties.get('gridProperties', {})
        actual_rows = grid_props.get('rowCount', 0)
        actual_cols = grid_props.get('columnCount', 0)
        
        # Limit range if too large
        if actual_rows > max_rows:
            print(f"  ⚠ Limiting to {max_rows} rows (sheet has {actual_rows})", file=sys.stderr)
            range_notation = f"'{sheet_name}'!A1:ZZZ{max_rows}"
        else:
            range_notation = sheet_name
        
        # Fetch sheet data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueRenderOption='FORMATTED_VALUE'  # Get formatted values (dates as strings)
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return {
                'sheet_name': sheet_name,
                'is_empty': True,
                'rows': []
            }
        
        # Extract headers (first row)
        headers = values[0] if values else []
        
        # Normalize headers (ensure unique)
        normalized_headers = []
        seen = {}
        for i, header in enumerate(headers):
            header = str(header).strip() if header else f"Column{i+1}"
            if header in seen:
                seen[header] += 1
                header = f"{header}_{seen[header]}"
            else:
                seen[header] = 0
            normalized_headers.append(header)
        
        # Convert to list of row dictionaries
        rows = []
        for row_values in values[1:]:  # Skip header row
            # Pad row to match header length
            padded_row = row_values + [''] * (len(normalized_headers) - len(row_values))
            
            # Create row dict
            row_dict = {}
            for header, value in zip(normalized_headers, padded_row):
                row_dict[header] = value if value != '' else None
            
            rows.append(row_dict)
        
        return {
            'sheet_name': sheet_name,
            'is_empty': False,
            'dimensions': {
                'rows': len(rows),
                'columns': len(normalized_headers)
            },
            'headers': normalized_headers,
            'data': rows
        }
        
    except Exception as e:
        print(f"  ✗ Error extracting sheet '{sheet_name}': {str(e)}", file=sys.stderr)
        return {
            'sheet_name': sheet_name,
            'error': str(e),
            'rows': []
        }

def extract_spreadsheet_data(url_or_id: str, max_rows_per_sheet: int = 5000) -> Dict:
    """
    Extract all data from a Google Spreadsheet in LLM-friendly format.
    
    Args:
        url_or_id: Google Sheets URL or spreadsheet ID
        max_rows_per_sheet: Maximum rows to extract per sheet
        
    Returns:
        Dictionary with complete spreadsheet data
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
        
        # Extract data from each sheet
        sheets_data = []
        for sheet_name in sheet_names:
            print(f"Extracting: {sheet_name}...", file=sys.stderr)
            sheet_data = extract_sheet_data(service, spreadsheet_id, sheet_name, max_rows_per_sheet)
            sheets_data.append(sheet_data)
        
        # Compile result
        result = {
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            'title': title,
            'locale': locale,
            'timezone': timezone,
            'sheet_count': len(sheets),
            'sheets': sheets_data,
            'summary': {
                'total_sheets': len(sheets),
                'sheet_names': sheet_names,
                'total_data_rows': sum(s.get('dimensions', {}).get('rows', 0) for s in sheets_data)
            }
        }
        
        return {
            'status': 'success',
            'data': result
        }
        
    except FileNotFoundError as e:
        return {'status': 'error', 'message': str(e)}
    except HttpError as error:
        return {'status': 'error', 'message': f"Google API error: {error}"}
    except Exception as error:
        return {'status': 'error', 'message': f"Unexpected error: {error}"}

def main():
    """Main entry point for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python extract_sheet_data.py <spreadsheet_url_or_id> [max_rows_per_sheet]")
        sys.exit(1)
    
    url_or_id = sys.argv[1]
    max_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    print(f"Extracting spreadsheet data...", file=sys.stderr)
    result = extract_spreadsheet_data(url_or_id, max_rows)
    
    if result['status'] == 'success':
        data = result['data']
        spreadsheet_id = data['spreadsheet_id']
        
        # Save to .tmp directory
        tmp_dir = Path(__file__).parent.parent / '.tmp'
        tmp_dir.mkdir(exist_ok=True)
        
        output_file = tmp_dir / f"sheet_data_{spreadsheet_id}.json"
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        
        print(f"\n✓ Extraction complete!", file=sys.stderr)
        print(f"  Spreadsheet: {data['title']}", file=sys.stderr)
        print(f"  Sheets: {data['sheet_count']}", file=sys.stderr)
        print(f"  Total data rows: {data['summary']['total_data_rows']}", file=sys.stderr)
        print(f"  Output: {output_file}", file=sys.stderr)
        
        sys.exit(0)
    else:
        print(f"\n✗ Error: {result['message']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
