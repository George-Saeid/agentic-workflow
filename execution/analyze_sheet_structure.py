"""
Google Sheet Structure Analyzer
Extracts and analyzes the complete structure of a Google Sheet.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for Google Sheets API (read-only)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Google Sheets epoch (December 30, 1899)
SHEETS_EPOCH = datetime(1899, 12, 30)

def serial_to_date(serial_number: float) -> str:
    """
    Convert Google Sheets serial number to date string.
    
    Args:
        serial_number: The numeric date value from Google Sheets
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    try:
        date = SHEETS_EPOCH + timedelta(days=serial_number)
        return date.strftime('%Y-%m-%d')
    except (ValueError, OverflowError):
        return str(serial_number)

def extract_spreadsheet_id(url_or_id: str) -> str:
    """
    Extract spreadsheet ID from URL or return if already an ID.
    
    Args:
        url_or_id: Google Sheets URL or spreadsheet ID
        
    Returns:
        Spreadsheet ID
    """
    # Pattern to match spreadsheet ID in URL
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url_or_id)
    
    if match:
        return match.group(1)
    
    # If no match, assume it's already an ID
    return url_or_id.strip()

def get_google_sheets_service():
    """
    Authenticate and return Google Sheets API service.
    
    Returns:
        Google Sheets API service object
    """
    creds = None
    project_root = Path(__file__).parent.parent
    token_path = project_root / 'token.json'
    credentials_path = project_root / 'credentials.json'
    
    # Check if credentials.json exists
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {credentials_path}\n"
            "Please download OAuth credentials from Google Cloud Console"
        )
    
    # Load existing token if available
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        token_path.write_text(creds.to_json())
    
    return build('sheets', 'v4', credentials=creds)

def infer_data_type(value: Any) -> str:
    """
    Infer the data type of a cell value.
    
    Args:
        value: Cell value
        
    Returns:
        Data type as string
    """
    if value is None or value == '':
        return 'empty'
    
    # Try to determine type
    str_value = str(value).strip()
    
    # Check for number
    try:
        float(str_value.replace(',', ''))
        return 'number'
    except ValueError:
        pass
    
    # Check for boolean
    if str_value.lower() in ['true', 'false', 'yes', 'no']:
        return 'boolean'
    
    # Check for date patterns (basic)
    date_patterns = [
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{1,2}-\d{1,2}-\d{2,4}$'
    ]
    for pattern in date_patterns:
        if re.match(pattern, str_value):
            return 'date'
    
    # Check for URL
    if str_value.startswith('http://') or str_value.startswith('https://'):
        return 'url'
    
    # Check for email
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str_value):
        return 'email'
    
    # Default to text
    return 'text'

def get_cell_type(cell_data: Dict) -> str:
    """
    Determine the type of a cell based on its metadata.
    
    Args:
        cell_data: Cell data from Google Sheets API
        
    Returns:
        Cell type as string
    """
    # Check for data validation (dropdown, checkbox)
    if 'dataValidation' in cell_data:
        validation = cell_data['dataValidation']
        if 'condition' in validation:
            condition_type = validation['condition'].get('type', '')
            if condition_type == 'BOOLEAN':
                return 'checkbox'
            elif condition_type in ['ONE_OF_RANGE', 'ONE_OF_LIST']:
                return 'dropdown'
    
    # Check for formula
    if 'userEnteredValue' in cell_data:
        user_value = cell_data['userEnteredValue']
        if 'formulaValue' in user_value:
            return 'formula'
    
    # Check for plain data
    if 'effectiveValue' in cell_data:
        effective = cell_data['effectiveValue']
        if 'numberValue' in effective:
            return 'number'
        elif 'stringValue' in effective:
            return 'text'
        elif 'boolValue' in effective:
            return 'boolean'
    
    return 'empty'

def extract_formula(cell_data: Dict) -> Optional[str]:
    """Extract formula from cell if it exists."""
    if 'userEnteredValue' in cell_data:
        user_value = cell_data['userEnteredValue']
        if 'formulaValue' in user_value:
            return user_value['formulaValue']
    return None

def extract_dropdown_options(cell_data: Dict) -> Optional[List[str]]:
    """Extract dropdown options from data validation."""
    if 'dataValidation' in cell_data:
        validation = cell_data['dataValidation']
        if 'condition' in validation:
            condition = validation['condition']
            if condition.get('type') in ['ONE_OF_LIST']:
                if 'values' in condition:
                    return [v.get('userEnteredValue', '') for v in condition['values']]
    return None

def normalize_formula(formula: str) -> str:
    """
    Normalize a formula by replacing cell references with placeholders.
    This helps identify formula patterns.
    
    Args:
        formula: The formula string
        
    Returns:
        Normalized formula pattern
    """
    if not formula:
        return ""
    
    # Replace absolute references like $A$1 with {ABS}
    normalized = re.sub(r'\$[A-Z]+\$\d+', '{ABS}', formula)
    
    # Replace column-absolute references like $A1 with {COL_ABS}
    normalized = re.sub(r'\$[A-Z]+\d+', '{COL_ABS}', normalized)
    
    # Replace row-absolute references like A$1 with {ROW_ABS}
    normalized = re.sub(r'[A-Z]+\$\d+', '{ROW_ABS}', normalized)
    
    # Replace relative references like A1 with {REL}
    normalized = re.sub(r'[A-Z]+\d+', '{REL}', normalized)
    
    return normalized

def analyze_formula_ranges(row_data: List[Dict], col_idx: int, start_row: int = 1) -> List[Dict]:
    """
    Analyze formula ranges in a column - where they start, end, and any breaks.
    
    Args:
        row_data: Row data from Google Sheets API
        col_idx: Column index to analyze
        start_row: Row to start analysis from
        
    Returns:
        List of formula range dictionaries
    """
    ranges = []
    current_range = None
    
    for row_idx in range(start_row, len(row_data)):
        row = row_data[row_idx]
        
        if 'values' in row and col_idx < len(row['values']):
            cell = row['values'][col_idx]
            formula = extract_formula(cell)
            
            if formula:
                # Normalize formula to detect pattern
                pattern = normalize_formula(formula)
                
                if current_range is None:
                    # Start new range
                    current_range = {
                        'start_row': row_idx,
                        'end_row': row_idx,
                        'pattern': pattern,
                        'first_formula': formula,
                        'formula_count': 1,
                        'formulas': [formula]
                    }
                elif current_range['pattern'] == pattern:
                    # Continue current range
                    current_range['end_row'] = row_idx
                    current_range['formula_count'] += 1
                    if len(current_range['formulas']) < 3:  # Keep first 3 examples
                        current_range['formulas'].append(formula)
                else:
                    # Pattern changed, save current range and start new one
                    ranges.append(current_range)
                    current_range = {
                        'start_row': row_idx,
                        'end_row': row_idx,
                        'pattern': pattern,
                        'first_formula': formula,
                        'formula_count': 1,
                        'formulas': [formula]
                    }
            else:
                # No formula - this is a break
                if current_range is not None:
                    # Save the current range
                    ranges.append(current_range)
                    current_range = None
        else:
            # Empty cell or out of bounds - also a break
            if current_range is not None:
                ranges.append(current_range)
                current_range = None
    
    # Don't forget the last range if it exists
    if current_range is not None:
        ranges.append(current_range)
    
    return ranges

def analyze_column_types(grid_data: List[Dict], start_row: int = 1) -> Dict[int, Dict]:
    """
    Analyze cell types and data types for each column.
    
    Args:
        grid_data: Grid data from Google Sheets API
        start_row: Row to start analysis from (skip headers)
        
    Returns:
        Dictionary with column analysis
    """
    if not grid_data:
        return {}
    
    row_data = grid_data[0].get('rowData', [])
    if not row_data or len(row_data) <= start_row:
        return {}
    
    # Determine max columns
    max_cols = 0
    for row in row_data:
        if 'values' in row:
            max_cols = max(max_cols, len(row['values']))
    
    column_analysis = {}
    
    for col_idx in range(max_cols):
        cell_types = []
        data_types = []
        formulas = []
        has_dropdown = False
        dropdown_options = None
        
        for row_idx in range(start_row, len(row_data)):
            row = row_data[row_idx]
            if 'values' in row and col_idx < len(row['values']):
                cell = row['values'][col_idx]
                
                # Get cell type
                cell_type = get_cell_type(cell)
                cell_types.append(cell_type)
                
                # Extract formula if exists
                formula = extract_formula(cell)
                if formula:
                    formulas.append(formula)
                
                # Check for dropdown
                if cell_type == 'dropdown':
                    has_dropdown = True
                    options = extract_dropdown_options(cell)
                    if options and not dropdown_options:
                        dropdown_options = options
                
                # Infer data type from effective value
                if 'effectiveValue' in cell:
                    effective = cell['effectiveValue']
                    if 'stringValue' in effective:
                        data_types.append(infer_data_type(effective['stringValue']))
                    elif 'numberValue' in effective:
                        data_types.append('number')
                    elif 'boolValue' in effective:
                        data_types.append('boolean')
        
        if cell_types:
            cell_type_counts = Counter(cell_types)
            dominant_cell_type = cell_type_counts.most_common(1)[0][0]
            cell_type_distribution = {t: count/len(cell_types) for t, count in cell_type_counts.items()}
        else:
            dominant_cell_type = 'empty'
            cell_type_distribution = {'empty': 1.0}
        
        if data_types:
            data_type_counts = Counter(data_types)
            dominant_data_type = data_type_counts.most_common(1)[0][0]
            data_type_distribution = {t: count/len(data_types) for t, count in data_type_counts.items()}
        else:
            dominant_data_type = 'empty'
            data_type_distribution = {'empty': 1.0}
        
        column_info = {
            'column_index': col_idx,
            'column_letter': chr(65 + col_idx) if col_idx < 26 else f"Col{col_idx}",
            'dominant_cell_type': dominant_cell_type,
            'cell_type_distribution': cell_type_distribution,
            'dominant_data_type': dominant_data_type,
            'data_type_distribution': data_type_distribution,
            'non_empty_count': len([t for t in cell_types if t != 'empty'])
        }
        
        # Analyze formula ranges and flow
        if formulas:
            formula_ranges = analyze_formula_ranges(row_data, col_idx, start_row)
            
            # Prepare formula flow information
            formula_flow = []
            for range_info in formula_ranges:
                flow_entry = {
                    'start_row': range_info['start_row'] + 1,  # Convert to 1-based
                    'end_row': range_info['end_row'] + 1,  # Convert to 1-based
                    'row_count': range_info['formula_count'],
                    'pattern': range_info['pattern'],
                    'first_formula': range_info['first_formula'],
                    'examples': range_info['formulas'][:3]  # First 3 examples
                }
                
                # Check if there's a break after this range
                if range_info['end_row'] < len(row_data) - 1:
                    # Check next few rows for continuation
                    next_formula_row = None
                    for check_row in range(range_info['end_row'] + 1, min(range_info['end_row'] + 10, len(row_data))):
                        if check_row < len(row_data):
                            check_row_data = row_data[check_row]
                            if 'values' in check_row_data and col_idx < len(check_row_data['values']):
                                check_cell = check_row_data['values'][col_idx]
                                if extract_formula(check_cell):
                                    next_formula_row = check_row + 1  # 1-based
                                    break
                    
                    if next_formula_row:
                        flow_entry['break_after'] = True
                        flow_entry['continues_at_row'] = next_formula_row
                        flow_entry['break_size'] = next_formula_row - flow_entry['end_row'] - 1
                
                formula_flow.append(flow_entry)
            
            column_info['formula_count'] = len(formulas)
            column_info['formula_ranges'] = len(formula_ranges)
            column_info['formula_flow'] = formula_flow
        
        # Add dropdown info if applicable
        if has_dropdown:
            column_info['has_dropdown'] = True
            if dropdown_options:
                column_info['dropdown_options'] = dropdown_options
        
        column_analysis[col_idx] = column_info
    
    return column_analysis

def analyze_sheet(service, spreadsheet_id: str, sheet_name: str, sheet_id: int, max_rows: int = 5000) -> Dict:
    """
    Analyze structure of a single sheet.
    
    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to analyze
        sheet_id: ID of the sheet
        max_rows: Maximum number of rows to fetch (default 5000)
        
    Returns:
        Dictionary with sheet analysis
    """
    try:
        # First, get sheet properties to check dimensions
        metadata = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[sheet_name],
            includeGridData=False
        ).execute()
        
        sheets = metadata.get('sheets', [])
        if sheets:
            properties = sheets[0].get('properties', {})
            grid_props = properties.get('gridProperties', {})
            actual_rows = grid_props.get('rowCount', 0)
            actual_cols = grid_props.get('columnCount', 0)
            
            # If sheet is very large, limit the range
            if actual_rows > max_rows:
                print(f"  ⚠ Sheet has {actual_rows} rows, limiting to {max_rows} rows", file=sys.stderr)
                range_notation = f"'{sheet_name}'!A1:ZZZ{max_rows}"
            else:
                range_notation = sheet_name
        else:
            range_notation = sheet_name
        
        # Fetch sheet data with full cell metadata
        result = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[range_notation],
            includeGridData=True
        ).execute()
        
        sheets = result.get('sheets', [])
        if not sheets:
            return {
                'sheet_name': sheet_name,
                'is_empty': True,
                'row_count': 0,
                'column_count': 0
            }
        
        sheet_data = sheets[0]
        grid_data = sheet_data.get('data', [])
        
        if not grid_data or not grid_data[0].get('rowData'):
            return {
                'sheet_name': sheet_name,
                'is_empty': True,
                'row_count': 0,
                'column_count': 0
            }
        
        row_data = grid_data[0].get('rowData', [])
        
        # Basic dimensions
        row_count = len(row_data)
        column_count = 0
        for row in row_data:
            if 'values' in row:
                column_count = max(column_count, len(row['values']))
        
        # Extract column headers (first row)
        column_headers = []
        if row_data and 'values' in row_data[0]:
            for cell in row_data[0]['values']:
                # First try formattedValue (what the user sees)
                if 'formattedValue' in cell:
                    column_headers.append(cell['formattedValue'])
                elif 'effectiveValue' in cell:
                    effective = cell['effectiveValue']
                    if 'stringValue' in effective:
                        column_headers.append(effective['stringValue'])
                    elif 'numberValue' in effective:
                        num_val = effective['numberValue']
                        # Check if this might be a date (reasonable date range)
                        # Google Sheets dates: 1 = 1899-12-31, 44927 = 2023-01-01, etc.
                        if 1 < num_val < 100000 and 'effectiveFormat' in cell:
                            # Check if cell has date formatting
                            number_format = cell.get('effectiveFormat', {}).get('numberFormat', {})
                            format_type = number_format.get('type', '')
                            if format_type == 'DATE' or format_type == 'DATE_TIME':
                                column_headers.append(serial_to_date(num_val))
                            else:
                                column_headers.append(str(num_val))
                        else:
                            column_headers.append(str(num_val))
                    elif 'boolValue' in effective:
                        column_headers.append(str(effective['boolValue']))
                    else:
                        column_headers.append('')
                else:
                    column_headers.append('')
        
        # Extract row headers (first column)
        row_headers = []
        for row in row_data[:10]:  # First 10 rows only
            if 'values' in row and len(row['values']) > 0:
                cell = row['values'][0]
                # First try formattedValue (what the user sees)
                if 'formattedValue' in cell:
                    row_headers.append(cell['formattedValue'])
                elif 'effectiveValue' in cell:
                    effective = cell['effectiveValue']
                    if 'stringValue' in effective:
                        row_headers.append(effective['stringValue'])
                    elif 'numberValue' in effective:
                        num_val = effective['numberValue']
                        # Check if this might be a date
                        if 1 < num_val < 100000 and 'effectiveFormat' in cell:
                            number_format = cell.get('effectiveFormat', {}).get('numberFormat', {})
                            format_type = number_format.get('type', '')
                            if format_type == 'DATE' or format_type == 'DATE_TIME':
                                row_headers.append(serial_to_date(num_val))
                            else:
                                row_headers.append(str(num_val))
                        else:
                            row_headers.append(str(num_val))
                    else:
                        row_headers.append('')
                else:
                    row_headers.append('')
            else:
                row_headers.append('')
        
        # Analyze column types and data
        column_analysis = analyze_column_types(grid_data, start_row=1)
        
        # Get sheet properties
        sheet_props = sheet_data.get('properties', {})
        
        analysis = {
            'sheet_name': sheet_name,
            'sheet_id': sheet_id,
            'is_empty': False,
            'dimensions': {
                'row_count': row_count,
                'column_count': column_count
            },
            'column_headers': column_headers,
            'row_headers': row_headers,
            'columns': column_analysis,
            'grid_properties': sheet_props.get('gridProperties', {})
        }
        
        return analysis
        
    except HttpError as error:
        return {
            'sheet_name': sheet_name,
            'error': str(error)
        }

def analyze_spreadsheet(url_or_id: str) -> Dict:
    """
    Analyze complete structure of a Google Spreadsheet.
    
    Args:
        url_or_id: Google Sheets URL or spreadsheet ID
        
    Returns:
        Dictionary with complete analysis
    """
    try:
        # Extract spreadsheet ID
        spreadsheet_id = extract_spreadsheet_id(url_or_id)
        
        # Get Google Sheets service
        service = get_google_sheets_service()
        
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        # Extract basic info
        title = spreadsheet.get('properties', {}).get('title', 'Unknown')
        locale = spreadsheet.get('properties', {}).get('locale', 'unknown')
        timezone = spreadsheet.get('properties', {}).get('timeZone', 'unknown')
        
        # Get all sheets
        sheets = spreadsheet.get('sheets', [])
        sheet_info = [(sheet['properties']['title'], sheet['properties']['sheetId']) for sheet in sheets]
        
        # Analyze each sheet
        sheet_analyses = []
        for sheet_name, sheet_id in sheet_info:
            print(f"Analyzing sheet: {sheet_name}...", file=sys.stderr)
            try:
                analysis = analyze_sheet(service, spreadsheet_id, sheet_name, sheet_id)
                sheet_analyses.append(analysis)
            except Exception as e:
                print(f"  ⚠ Error analyzing sheet '{sheet_name}': {str(e)}", file=sys.stderr)
                # Add error entry for this sheet
                sheet_analyses.append({
                    'sheet_name': sheet_name,
                    'sheet_id': sheet_id,
                    'error': str(e),
                    'status': 'error'
                })
        
        # Extract sheet names for summary
        sheet_names = [name for name, _ in sheet_info]
        
        # Compile complete analysis
        complete_analysis = {
            'spreadsheet_id': spreadsheet_id,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            'title': title,
            'locale': locale,
            'timezone': timezone,
            'sheet_count': len(sheets),
            'sheets': sheet_analyses,
            'analysis_summary': {
                'total_sheets': len(sheets),
                'non_empty_sheets': sum(1 for s in sheet_analyses if not s.get('is_empty', False)),
                'total_rows': sum(s.get('dimensions', {}).get('row_count', 0) for s in sheet_analyses),
                'sheet_names': sheet_names
            }
        }
        
        return {
            'status': 'success',
            'data': complete_analysis
        }
        
    except FileNotFoundError as e:
        return {
            'status': 'error',
            'message': str(e)
        }
    except HttpError as error:
        return {
            'status': 'error',
            'message': f"Google API error: {error}"
        }
    except Exception as error:
        return {
            'status': 'error',
            'message': f"Unexpected error: {error}"
        }

def main():
    """Main entry point for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_sheet_structure.py <spreadsheet_url_or_id>")
        sys.exit(1)
    
    url_or_id = sys.argv[1]
    
    print(f"Analyzing spreadsheet...")
    result = analyze_spreadsheet(url_or_id)
    
    if result['status'] == 'success':
        # Save to .tmp directory
        spreadsheet_id = result['data']['spreadsheet_id']
        tmp_dir = Path(__file__).parent.parent / '.tmp'
        tmp_dir.mkdir(exist_ok=True)
        
        output_file = tmp_dir / f"sheet_analysis_{spreadsheet_id}.json"
        output_file.write_text(json.dumps(result['data'], indent=2, ensure_ascii=False), encoding='utf-8')
        
        print(f"\n✓ Analysis complete!")
        print(f"  Spreadsheet: {result['data']['title']}")
        print(f"  Sheets: {result['data']['sheet_count']}")
        print(f"  Total rows: {result['data']['analysis_summary']['total_rows']}")
        print(f"  Output: {output_file}")
        
        sys.exit(0)
    else:
        print(f"\n✗ Error: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
