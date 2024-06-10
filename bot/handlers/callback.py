import asyncio
import os

from aiogram import Bot
from aiogram.types import CallbackQuery
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.basic import ready_report_broadcaster_container
from main import get_reports, get_link_to_report, download_report
from google_sheets import auth_and_update, read_csv, get_url_to_spreadsheet, auth_and_update_by_batches
from google_drive import auth_and_update_drive, get_url_to_drive
from api import create_report, get_report_status, notify_report_ready, notify_google_sheets_updated, notify_google_drive_updated


REPORT_PREFIX = "report_builder_clientId_155_masterId_1190_name_"
DATE_PREFIX = "date_"


def report_name_builder(report: str):
    report_type, report_date = report.split('_')
    report_name = f"{REPORT_PREFIX}{report_type}_{DATE_PREFIX}{report_date}"
    return report_name


async def handle_all_reports(query: CallbackQuery):
    async def reports_keyboard_builder(reports):
        inline_keyboard = []
        for report in reports:
            inline_keyboard.append([InlineKeyboardButton(
                text=report['name'].replace(REPORT_PREFIX, "").replace(DATE_PREFIX, "").replace('.csv', ''),
                callback_data=f"download_report|{report['name'].replace(REPORT_PREFIX, '').replace(DATE_PREFIX, '').replace('.csv', '')}"
            )])
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    all_reports = get_reports()
    await query.message.answer(f"All reports: ",
                               reply_markup=await reports_keyboard_builder(all_reports[:10]))
    await query.answer()


def create_report_title_for_button(report):
    return report.replace(REPORT_PREFIX, "").replace(DATE_PREFIX, "").replace('.csv', "")

async def handle_create_report(query: CallbackQuery, bot: Bot):
    _, report_type = query.data.split("|")
    await query.message.answer(
        f"{report_type}: the report will be generated in a few minutes. \nI will notify you when it will be ready")
    report = create_report(report_type)
    await query.message.answer("You can check status of generating report by yourself: ",
                               reply_markup=InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [
                                        InlineKeyboardButton(
                                            text="Check status",
                                            callback_data=f"check_status|{create_report_title_for_button(report['name'])}"
                                        )
                                    ]
                                ]
                            ))
    #asyncio.create_task(notify_report_ready(bot, report["name"], query.message.chat.id))
    ready_report_broadcaster_container.append((report["name"], query.message.chat.id))


async def handle_check_status(query: CallbackQuery):
    _, report = query.data.split('|')
    report_name = f"{report_name_builder(report)}.csv"
    result = await get_report_status(report_name)
    await query.answer(f"Report status: {result}", show_alert=True)


async def handle_download_report(query: CallbackQuery):
    _, report = query.data.split('|')
    report_name = f"{report_name_builder(report)}"
    link = await get_link_to_report(report_name)
    print(link)
    await query.message.answer(
        f"Link to download: \n<a href='{link}'>{report_name}</a>", parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Update in Google Spreadsheet",
                    callback_data=f"update_sheet|{report}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Update in Google Drive",
                    callback_data=f"update_drive|{report}"
                )
            ]
        ]),
    )
    await query.answer()


async def do(link, report_name, url, chat_id, response_id, bot: Bot):
    file_name = f"./reports_base/{report_name.replace(':', 'colon')}.csv"
    try:
        download_report(report_url=link, filename=file_name, path_to_save="reports_base")
        csv_values = read_csv(file_name)
        await auth_and_update_by_batches(csv_values=csv_values, google_url=url)
        await bot.send_message(chat_id,
                                      f'Report is ready.', reply_to_message_id=response_id)
    except Exception as e:
        print(f"Google spreadsheet update failed: {e}")
        await bot.send_message(chat_id,
                               f'Report export to google spreadsheets failed, please try again.',
                               reply_to_message_id=response_id)
    finally:
        if os.path.isfile(file_name):
            os.remove(file_name)


async def handle_sheet_update(query: CallbackQuery, bot: Bot):
    _, report = query.data.split('|')
    await query.message.reply("Start updating google spreadsheet")
    report_name = f"{report_name_builder(report)}"
    link = await get_link_to_report(report_name)
    url = get_url_to_spreadsheet(report_name)
    message = await notify_google_sheets_updated(bot, query.message.chat.id, url)

    asyncio.create_task(do(link, report_name, url, query.message.chat.id, message.message_id, bot))


async def handler_drive_update(query: CallbackQuery, bot: Bot):
    _, report = query.data.split('|')
    await query.message.reply("Start updating google drive file")
    report_name = f"{report_name_builder(report)}"
    filepath = f"./reports_base/{report_name.replace(':', 'colon')}.csv"
    try:
        link = await get_link_to_report(report_name)
        download_report(report_url=link, filename=filepath, path_to_save="reports_base")
        drive_url = get_url_to_drive(report_name)
        auth_and_update_drive(local_path=filepath, drive_url=drive_url)
        await notify_google_drive_updated(bot, query.message.chat.id, drive_url)
    except Exception as e:
        print(f"Google drive update failed: {e}]")
        await bot.send_message(query.message.chat.id,
                               f'Report export to google drive failed: {e}, please try again.')
    finally:
        if os.path.isfile(filepath):
            os.remove(filepath)
