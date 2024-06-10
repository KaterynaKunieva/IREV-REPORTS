from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

main_keyboard_builder = InlineKeyboardBuilder()
main_keyboard_builder.add(
    InlineKeyboardButton(text="Show all reports", callback_data="get_reports|"),
    InlineKeyboardButton(text="Create Sale Statuses Report", callback_data="create_report|Sale Statuses Report"),
    InlineKeyboardButton(text="Create Leads Report", callback_data="create_report|Leads Report"),
    InlineKeyboardButton(text="Create Leads Push Logs Report", callback_data="create_report|Leads Push Logs Report")
)
main_keyboard_builder.adjust(1)
main_keyboard_markup = main_keyboard_builder.as_markup()