from re import findall
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


def extract_file_id(url):
    pattern = r'/file/d/([a-zA-Z0-9-_]+)'
    return findall(pattern, url)[0]


def auth_google():
    service_account_file = './googledrive.json'
    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=creds)
    return service


def update_csv(service, local_path, google_file_id):
    try:
        media_body = MediaFileUpload(local_path, mimetype='text/csv')
        updated_file = service.files().update(
            fileId=google_file_id,
            media_body=media_body
        ).execute()
        print(f"File updated successfully: {updated_file['id']}")
    except Exception as e:
        print(f"Error updating the file: {e}")


def get_url_to_drive(report_name):
    reports_url = {
        "sale-statuses-report": "https://drive.google.com/file/d/1ImsXzxGnmTBHpiqrMTpfMc91-u9Ce6vt/view?usp=drive_link",
        "leads-report": "https://drive.google.com/file/d/1xQ5c3RD5F1Pw24YSpBfARw26ERLDbSPS/view?usp=drive_link",
        "lead-push-log-report": "https://drive.google.com/file/d/1J2fDp2iUWa0kqeVgrrwzLYRYH9ZQPa1M/view?usp=drive_link"
    }
    report_type = findall(r"([a-z-]+)-report", report_name)[0]
    return reports_url.get(f"{report_type}-report")


def auth_and_update_drive(local_path, drive_url):
    file_id = extract_file_id(drive_url)
    service = auth_google()
    update_csv(service=service, local_path=local_path, google_file_id=file_id)


if __name__ == "__main__":
    CSV_FILE_PATH = 'reports_base/report_builder_clientId_155_masterId_1190_name_lead-push-log-report_date_2024-05-29T05_11_05.418Z.csv'
    DRIVE_URL = get_url_to_drive(CSV_FILE_PATH)
    auth_and_update_drive(local_path=CSV_FILE_PATH, drive_url=DRIVE_URL)
