from asyncio import Task

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram import F

import asyncio
import logging

from api import notify_report_ready
from settings import settings
from bot.handlers.basic import cmd_start, ready_report_broadcaster_container
from bot.handlers.callback import handle_all_reports, handle_create_report, handle_download_report, \
    handle_sheet_update, handle_check_status, handler_drive_update
from bot.utils.commands import set_commands


async def start_bot():
    task: Task = None
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    bot = Bot(token=settings.bots.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    dp = Dispatcher()

    # commands registration
    await set_commands(bot=bot)
    dp.message.register(cmd_start, Command('start'), F.chat.func(lambda chat: chat.id in settings.bots.allowed_chats))

    # callbacks registration
    dp.callback_query.register(handle_all_reports, F.data.startswith('get_reports|'))
    dp.callback_query.register(handle_create_report, F.data.startswith('create_report|'))
    dp.callback_query.register(handle_check_status, F.data.startswith('check_status|'))
    dp.callback_query.register(handle_download_report, F.data.startswith('download_report|'))
    dp.callback_query.register(handle_sheet_update, F.data.startswith('update_sheet|'))
    dp.callback_query.register(handler_drive_update, F.data.startswith('update_drive|'))

    logger.info("Bot is starting...")

    async def on_startup():
        logging.info('Bot is starting up...')
        global task
        task = asyncio.create_task(notify_report_ready(bot, ready_report_broadcaster_container))

    dp.startup.register(on_startup)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot has stopped.")
        if task:
            task.cancel()


if __name__ == '__main__':
    asyncio.run(start_bot())

