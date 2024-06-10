from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

from main import get_report_type, create_new_report, get_last_report, get_reports, get_link_to_report
import time
from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode

REPORT_PREFIX = "report_builder_clientId_155_masterId_1190_name_"
DATE_PREFIX = "date_"

async def get_report_status(report_filename):
    reports = get_reports()
    for report in reports:
        if report["name"] == report_filename:
            return report["status"]
    return False


def create_report(report_name):
    report_type = get_report_type(report_name)
    create_new_report(report_type=report_type)
    time.sleep(2)
    return get_last_report()

def create_report_title_for_button(report):
    return report.replace(REPORT_PREFIX, "").replace(DATE_PREFIX, "").replace('.csv', "")

async def notify_report_ready(bot: Bot, broadcast_container):
    waiting_update = False
    while True:
        if not waiting_update and broadcast_container:
            (report_name, chat_id) = broadcast_container.pop(0)
            waiting_update = True
            while waiting_update:
                try:
                    result = await get_report_status(report_name)
                    if result == 'Success':
                        link = await get_link_to_report(report_name)
                        await bot.send_message(
                            chat_id,
                            f"Report generated. Link to download: <a href='{link}'>{report_name}</a>",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="Update in Google Spreadsheet",
                                        callback_data=f"update_sheet|{create_report_title_for_button(report_name)}"
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        text="Update in Google Drive",
                                        callback_data=f"update_drive|{create_report_title_for_button(report_name)}"
                                    )
                                ],
                            ])
                        )
                        waiting_update = False
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"Couldn't deliver report-ready broadcast {e}")
                    waiting_update = False
        await asyncio.sleep(5)


async def notify_google_drive_updated(bot, chat, google_link):
    return await bot.send_message(chat, f'Report is updated. You can check it by link: {google_link}')


async def notify_google_sheets_updated(bot, chat, google_link):
    return await bot.send_message(chat, f'Report will be updated in few minutes. You can check it by link: {google_link}')

