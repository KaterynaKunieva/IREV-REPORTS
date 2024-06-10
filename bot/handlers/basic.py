
from aiogram import Bot
from aiogram.types import Message

from bot.keyboards.main_keyboard import main_keyboard_markup

ready_report_broadcaster_container = []
async def cmd_start(message: Message, bot: Bot):
    await bot.send_message(message.chat.id, 'Available commands in bot: ', reply_markup=main_keyboard_markup)
