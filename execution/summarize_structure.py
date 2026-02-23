"""Quick script to display sheet structure summary"""
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python summarize_structure.py <json_file>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n📊 Spreadsheet: {data['title']}")
print(f"🔗 URL: {data['spreadsheet_url']}")
print(f"🌍 {data['locale']} | {data['timezone']}")
print(f"\n📄 {data['sheet_count']} Sheets:\n")

for i, sheet in enumerate(data['sheets'], 1):
    if sheet.get('is_empty'):
        print(f"{i}. {sheet['sheet_name']}: EMPTY")
        continue
    
    if 'error' in sheet:
        print(f"{i}. {sheet['sheet_name']}: ERROR - {sheet['error']}")
        continue
    
    dims = sheet.get('dimensions', {})
    print(f"{i}. {sheet['sheet_name']}: {dims['rows']} rows × {dims['columns']} cols")
    
    # Column structure
    col_struct = sheet.get('column_structure', {})
    col_type = col_struct.get('type', 'unknown')
    
    if col_type == 'repeating':
        template = col_struct['template']
        repeat = col_struct['repeat_count']
        breaks = len(col_struct.get('breaks', []))
        print(f"   Columns: {template} × {repeat} blocks" + (f" ({breaks} breaks)" if breaks else ""))
    elif col_type == 'list':
        print(f"   Columns: {len(col_struct['values'])} items - {', '.join(col_struct['values'][:5])}...")
    elif col_type == 'varied_with_prefix':
        print(f"   Columns: {col_struct['total']} items, {col_struct['prefix_count']} start with '{col_struct['common_prefix']}'")
    elif col_type == 'date_sequence':
        print(f"   Columns: {col_struct['count']} dates from {col_struct['first']} to {col_struct['last']}")
    elif col_type == 'uniform':
        print(f"   Columns: All '{col_struct['value']}' ({col_struct['count']}x)")
    else:
        print(f"   Columns: {col_struct.get('unique_count', '?')} unique values")
    
    # Row structure
    row_struct = sheet.get('row_structure', {})
    row_type = row_struct.get('type', 'unknown')
    
    if row_type == 'list':
        print(f"   Rows: {', '.join(str(v) for v in row_struct['values'][:8])}{'...' if len(row_struct['values']) > 8 else ''}")
    elif row_type == 'varied_with_prefix':
        print(f"   Rows: {row_struct['prefix_count']}/{row_struct['total']} start with '{row_struct['common_prefix']}'")
    elif row_type == 'repeating':
        print(f"   Rows: {row_struct['template']} × {row_struct['repeat_count']} blocks")
    
    # Frozen info
    if 'frozen' in sheet:
        frozen = sheet['frozen']
        if frozen['rows'] or frozen['columns']:
            print(f"   Frozen: {frozen['rows']} rows, {frozen['columns']} columns")
    
    print()
