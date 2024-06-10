import asyncio
import csv
from re import findall
from googleapiclient.discovery import build
from google.oauth2 import service_account


def extract_sheets_id(url):
    pattern = '/spreadsheets/d/([a-zA-Z0-9_-]+)'
    matches = findall(pattern, url)
    if matches:
        return matches[0]
    else:
        print("No valid spreadsheet ID found in the URL.")
        exit(1)


def read_csv(file_path):
    with open(file_path, mode='r',  encoding='utf-8') as file:
        reader = csv.reader(file)
        data = list(reader)
    return data


def auth_google():
    service_account_file = './googledrive.json'
    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    import socket
    timeout_in_sec = 60 * 5
    socket.setdefaulttimeout(timeout_in_sec)
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_sheet_id(service, spreadsheet_id, sheet_name):
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for sheet in sheet_metadata['sheets']:
        if sheet['properties']['title'] == sheet_name:
            sheet_id = sheet['properties']['sheetId']
            break
    if sheet_id is None:
        print(f"Sheet '{sheet_name}' not found.")
    return sheet_id


def clear_sheet(service, spreadsheet_id, sheet_name):
    try:
        clear_request = {
            'requests': [{
                'updateCells': {
                    'range': {
                        'sheetId': get_sheet_id(service, spreadsheet_id, sheet_name)
                    },
                    'fields': 'userEnteredValue'
                }
            }]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=clear_request
        ).execute()
        print(f"Existing content in sheet '{sheet_name}' cleared.")
    except Exception as e:
        print(f"Error clearing the spreadsheet: {e}")
        exit(1)


def get_column_letter(column_index):
    """Convert a column index (1-based) to its corresponding letter name."""
    column_index -= 1  # Convert to 0-based index
    column_letter = ""
    while column_index >= 0:
        column_letter = chr(column_index % 26 + ord('A')) + column_letter
        column_index = column_index // 26 - 1
    return column_letter


def update_sheet(service, csv_values, spreadsheet_id, sheet_name, timeout=300):
    clear_sheet(service=service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    body = {
        'values': csv_values
    }
    retry_count = 3
    while retry_count > 0:
        try:
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"{result.get('updatedCells')} cells updated.")
            retry_count = 0
        except Exception as e:
            retry_count = retry_count-1
            print(e)
            print(retry_count)


def auth_and_update(csv_values, google_url, sheet_name="Sheet1"):
    spread_sheet_id = extract_sheets_id(google_url)
    service = auth_google()
    sheet_id = get_sheet_id(service=service, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)
    if sheet_id is None:
        exit(1)
    update_sheet(service=service, csv_values=csv_values, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)


def get_url_to_spreadsheet(report_name):
    reports_url = {
        "sale-statuses-report": "https://docs.google.com/spreadsheets/d/1xthxqy7TP7Ho7Wj2A8-J69dyuPJJOpiaJ7psRYk9fFI/edit?usp=sharing",
        "leads-report": "https://docs.google.com/spreadsheets/d/1syJAGUD9f5dc80T1hoXl9YcSXkoOqZtCERfhV0qGPPo/edit?usp=drive_link",
        "lead-push-log-report": "https://docs.google.com/spreadsheets/d/1_NCxbTA3z7qIMtanYEYqZQmb-Mm5YFcT4wIDQJXgMgc/edit?usp=drive_link"
    }
    report_type = findall(r"([a-z-]+)-report", report_name)[0]
    return reports_url.get(f"{report_type}-report")


# batches
def split_into_batches(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def update_sheet_by_batches(service, csv_values, spreadsheet_id, sheet_name, batch_size=1000):
    clear_sheet(service=service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    start_row = 1
    for batch in split_into_batches(csv_values, batch_size):
        column_index = len(batch[0])
        column_name = get_column_letter(column_index)
        body = {
            'values': batch
        }
        range_name = f'{sheet_name}!A{start_row}:{column_name}{start_row+len(batch)}'
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"{result.get('updatedCells')} cells updated in range {range_name}.")
        start_row += batch_size


async def auth_and_update_by_batches(csv_values, google_url, sheet_name="Sheet1"):
    spread_sheet_id = extract_sheets_id(google_url)
    service = auth_google()
    sheet_id = get_sheet_id(service=service, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)
    if sheet_id is None:
        exit(1)
    update_sheet(service=service, csv_values=csv_values, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)


def update_sheet_in_batches_filter(service, csv_values, spreadsheet_id, sheet_name, batch_size=1000):
    clear_sheet(service=service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    total_rows = len(csv_values)
    start_row = 0
    requests = []

    while start_row < total_rows:
        end_row = min(start_row + batch_size, total_rows)
        batch_data = csv_values[start_row:end_row]
        body = {
            'values': batch_data
        }
        values_obj = []
        for row in batch_data:
            values = []
            for x in row:
                values.append({"values": {"userEnteredValue": {"stringValue": x}}})
            values_obj.append(values)

        request = {
            'updateCells': {
                'range': {
                    'sheetId': 0,  # Adjust if your sheet ID is different
                    'startRowIndex': start_row,
                    'endRowIndex': end_row,
                    'startColumnIndex': 0,
                    'endColumnIndex': len(csv_values[0])  # Assuming all rows have the same number of columns
                },
                'rows': values_obj,
                'fields': 'userEnteredValue'
            }
        }

        requests.append(request)
        start_row += batch_size

    batch_body = {
        'requests': requests
    }

    try:
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=batch_body
        ).execute()
        print(f"{result.get('totalUpdatedCells')} cells updated.")
    except Exception as e:
        print(f"Error updating sheet: {e}")


def auth_and_update_by_batches_filter(csv_values, google_url, sheet_name="Sheet1"):
    csv_values = csv_values[:17000]
    spread_sheet_id = extract_sheets_id(google_url)
    service = auth_google()
    sheet_id = get_sheet_id(service=service, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)
    if sheet_id is None:
        exit(1)
    update_sheet_in_batches_filter(service=service, csv_values=csv_values, spreadsheet_id=spread_sheet_id, sheet_name=sheet_name)


if __name__ == '__main__':
    PATH_TO_FILE = "./reports_base/report_builder_clientId_155_masterId_1190_name_sale-statuses-report_date_2024-05-31T04_37_02.252Z.csv"
    URL_TO_FILE = "https://docs.google.com/spreadsheets/d/1syJAGUD9f5dc80T1hoXl9YcSXkoOqZtCERfhV0qGPPo/edit?usp=drive_link"
    CSV_VALUES = read_csv(PATH_TO_FILE)
    auth_and_update(csv_values=CSV_VALUES, google_url=URL_TO_FILE)
