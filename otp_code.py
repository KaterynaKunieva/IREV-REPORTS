import re
import datetime
import logging
from telethon import TelegramClient, events
from settings import settings

logging.basicConfig(filename="otp.log", level=logging.INFO)
logger = logging.getLogger(__name__)


# client = TelegramClient('session_name', api_id, api_hash)
client = TelegramClient('anon', settings.otp.api_id, settings.otp.api_hash)

logger.info(f"{datetime.datetime.now()}: bot launched")


def parse_code_from_text(text):
    logger.info(f"{datetime.datetime.now()}: Parsing OTP code")
    pattern = r'\d{4}'
    code = re.findall(pattern, text)[0]

    if not code:
        logger.info(f"No 2FA code found in the text.")
    return code


@client.on(events.NewMessage(chats=settings.otp.chats))
async def my_event_handler(event):
    logger.info(f"{datetime.datetime.now()}: OTP message received")
    with open('./code.txt', 'w+', encoding='utf-8') as f:
        f.seek(0)
        f.truncate(0)
        f.write(parse_code_from_text(event.raw_text))

client.start()
client.run_until_disconnected()
