from enum import Enum
import time

import requests
import json
from datetime import datetime
import dateutil.parser
import pytz


class GetTokenResponse(Enum):
    OTP = 1
    OK = 2
    BAD = 3


def generate_year_filter():
    timezone = None
    with open('./tokens.json', 'r+', encoding="utf-8") as f:
        json_token = json.load(f)
        timezone = json_token.get('start_token', '').get('timezone')
    return {
        "from": str(datetime.now(pytz.timezone(timezone)).replace(month=1, day=1, hour=0, minute=0, second=0,
                                                                  microsecond=0).strftime('%Y-%m-%dT00:00:00.000Z')),
        "to": str(datetime.now(pytz.timezone(timezone)).replace(month=12, day=31, hour=23, minute=59, second=59,
                                                                microsecond=59).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
    }


def post_handler(url, headers=None, data_params=None, json_params=None):
    try:
        r = requests.post(url=url, data=data_params, json=json_params, headers=headers)
        return r
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_otp_code():
    time.sleep(1)
    with open('./code.txt', 'r+', encoding='utf-8') as f:
        token = f.read()
        return token


def request_start_token(two_fa_token=None):
    url = 'https://id.irev.com/master/backend/api/wizard/v1/login'
    body = {
        "login": "kateryna@statsaff.net",
        "password": "S7zH4Gh2Kh",
        "token_2fa": two_fa_token,
        "redirect": ""
    }
    r = post_handler(url=url, data_params=body)
    response = r.json()
    if 'data' in response:
        print(f"Got token from {url}")
        data = response['data']
        return (GetTokenResponse.OK, {
            "access_token": data.get('access_token', ''),
            "expires_at": data.get('expires_at', ''),
            "timezone": data.get("user", {}).get('timezone', "")
        })
    elif response.get('error').get('otp'):
        print("Token for otp was sent to telegram")
        return (GetTokenResponse.OTP, response)
    return (GetTokenResponse.BAD, response)


def get_stat_ltd_token(start_token):
    url = 'https://stats-ldlt.irev.com/api/auth/v1/callback'
    body = {
        "domain": "stats-ldlt.irev.com"
    }
    headers = {
        "Authorization": f"Bearer {start_token}"
    }
    r = post_handler(url=url, headers=headers, data_params=body)
    if not r:
        return None
    print(f"Requested token for {url}")
    return r.json().get('data', {}).get('token', '')


def get_start_token():
    def check_token_expiration(expires_at, timezone):
        if not expires_at:
            return False
        expires_at_datetime = dateutil.parser.parse(expires_at)
        now_datetime = datetime.now(pytz.timezone(timezone))
        return expires_at_datetime > now_datetime

    def overwrite_content_file(file, content):
        file.seek(0)
        file.truncate()
        json.dump(content, f, indent=4)

    tokens_file_path = './tokens.json'
    token_type = 'start_token'
    try:
        with open(file=tokens_file_path, mode='r+', encoding='utf8') as f:
            json_obj = json.load(f)
            token_info = json_obj.get(token_type, {})
            token_valid = check_token_expiration(token_info.get('expires_at'), token_info.get("timezone"))
            if token_valid:
                print("Found valid start_token")
                return token_info.get("access_token")
            print(f"Token {token_type} not valid. Generating new one")
            new_token_info = login_with_2fa()
            json_obj[token_type] = new_token_info
            overwrite_content_file(file=f, content=json_obj)
            return new_token_info.get("access_token")
    except json.JSONDecodeError as decode_err:
        print(f'JSONDecodeError occurred: {decode_err}')


def login_with_2fa():
    start_token = None
    status, response = request_start_token()
    if status == GetTokenResponse.OTP:
        otp_code = get_otp_code()
        status, start_token = request_start_token(otp_code)
    return start_token


def get_reports():
    url = 'https://stats-ldlt.irev.com/api/crm/v1/widget/data'
    start_token = get_start_token()
    stat_ltd_token = get_stat_ltd_token(start_token)
    headers = {
        "Authorization": f"Bearer {stat_ltd_token}",
        "Client-Id": '155'
    }
    # get start of year and utcnow due to timezone in token.json
    body = {"widget": "DataExporter\\UserCsvList",
            "settings": {},
            **generate_year_filter()
            }

    r = post_handler(url=url, headers=headers, data_params=body)
    if not r:
        return None
    print("Requested all reports")
    return r.json().get('data', {}).get('data', [])


def get_last_report():
    def compare_reports_date(first_report, second_report):
        date1 = first_report.get('updatedAt', '')
        date2 = second_report.get('updatedAt', '')
        date1_datetime = dateutil.parser.parse(date1)
        date2_datetime = dateutil.parser.parse(date2)

        if date1_datetime > date2_datetime:
            return first_report
        else:
            return second_report

    reports_array = get_reports()
    if not reports_array or not len(reports_array):
        print('Reports not found')
        return None

    newest_report = reports_array[0]
    for i in range(1, len(reports_array)):
        next_report = reports_array[i]
        newest_report = compare_reports_date(newest_report, next_report)

    return newest_report


async def get_link_to_report(report_name):
    url = "https://stats-ldlt.irev.com/api/crm/v1/commands/process"
    start_token = get_start_token()
    stat_ltd_token = get_stat_ltd_token(start_token)
    headers = {
        "Authorization": f"Bearer {stat_ltd_token}",
        "Client-Id": '155',
    }
    body = {
        "action": "DataExporter\\GetCsvDownloadUrl",
        "arguments": {
            "name": (report_name.rstrip(".csv")) + ".csv"
        }
    }
    r = post_handler(url=url, headers=headers, json_params=body)
    if not r:
        return False
    print(f'Request link to report {report_name}')
    return r.json()["data"]


def download_report(report_url, filename, path_to_save=''):
    def save_to_onedrive(url, file):
        pass

    def save_csv_locally(path, file_content):
        path = path.replace(':', "colon")
        with open(path, mode='w+', encoding='utf-8') as f:
            f.write(file_content)
            print(f"File saved locally: {path}")

    try:
        r = requests.get(url=report_url)
        r.raise_for_status()
        content = r.content.decode('utf-8')
        save_csv_locally(filename, content)

    except Exception as e:
        print(e)


async def download_new_report(path_to_save=""):
    new_report = get_last_report()
    filename = new_report.get('name', '')
    link_to_download = await get_link_to_report(filename)
    download_report(link_to_download, filename, path_to_save)


def get_columns(report_type):
    url = 'https://stats-ldlt.irev.com/api/crm/v1/widget/data'
    body = {"widget": "DataExporter\\Available",
            "settings": {},
            **generate_year_filter()
            }
    start_token = get_start_token()
    stat_ltd_token = get_stat_ltd_token(start_token)
    headers = {
        "Authorization": f"Bearer {stat_ltd_token}",
        "Client-Id": '155'
    }
    print("Request for columns")
    r = post_handler(url=url, headers=headers, json_params=body)
    if not r:
        return None
    response = r.json()
    all_columns = []
    for info in response.get('data').get('data'):
        if info['key'] == report_type:
            for column in info.get('columns'):
                all_columns.append({'key': column['key']})
    return all_columns


def create_new_report(report_type):
    columns = get_columns(report_type=report_type)
    url = "https://stats-ldlt.irev.com/api/crm/v1/commands/process"
    start_token = get_start_token()
    stat_ltd_token = get_stat_ltd_token(start_token)
    headers = {
        "Authorization": f"Bearer {stat_ltd_token}",
        "Client-Id": '155',
    }
    request_start_token()
    code = get_otp_code()
    verify_body = {"action":"OTP\\VerifyCode","arguments":{"code":code,"section":"Data Exporter"}}
    r = post_handler(url=url, json_params=verify_body, headers=headers)
    print(r.json())

    conditions = []
    if report_type != 'lead-push-log-report':
        conditions.append({"config": "AND",
                                "key": "LeadModel.$lead#isTest",
                                "operator": "=",
                                "value": False})
    body = {
        "action": "DataExporter\\GenerateCsv",
        "arguments": {
            "name": report_type,
            "filters": {
                "date": generate_year_filter(),
                "conditions": conditions,
                "columns": columns,
                "dateBy": "createdAt"
            }
        }
    }
    r = post_handler(url=url, json_params=body, headers=headers)
    print(r.json())


def get_report_type(report_name):
    with open("./reports_type.json", 'r+', encoding='utf-8') as f:
        report_types = json.load(f)
        return report_types.get(report_name, '')


if __name__ == "__main__":
    pass
    # print(get_otp_code())
    # print(len(get_columns(get_report_type("Sale Statuses Report"))))
    # print(len(get_columns(get_report_type("Leads Report"))))
    # print(len(get_columns(get_report_type("Leads Push Logs Report"))))
        # async def test():
        #     link = await get_link_to_report(
        #         'report_builder_clientId_155_masterId_1190_name_leads-report_date_2024-05-29T05:16:49.847Z')
        #     print(link)
        #
        # asyncio.run(test())  # Await and run the async function using asyncio.run()
