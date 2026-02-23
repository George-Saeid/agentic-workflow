"""Quick script to summarize sheet analysis"""
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python summarize_analysis.py <json_file>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n📊 Spreadsheet: {data['title']}")
print(f"🔗 URL: {data['spreadsheet_url']}")
print(f"🌍 Locale: {data['locale']} | Timezone: {data['timezone']}")
print(f"\n📄 Sheets: {data['sheet_count']}\n")

for i, sheet in enumerate(data['sheets'], 1):
    if sheet.get('is_empty'):
        print(f"{i}. {sheet['sheet_name']}: EMPTY")
    elif 'error' in sheet:
        print(f"{i}. {sheet['sheet_name']}: ERROR - {sheet['error']}")
    else:
        dims = sheet.get('dimensions', {})
        rows = dims.get('row_count', 0)
        cols = dims.get('column_count', 0)
        print(f"{i}. {sheet['sheet_name']}: {rows} rows × {cols} columns")

print(f"\n📈 Total rows across all sheets: {data['analysis_summary']['total_rows']}")
