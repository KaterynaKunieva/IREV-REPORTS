from environs import Env
from dataclasses import dataclass


@dataclass
class Bots:
    bot_token: str
    allowed_chats: list[int]


@dataclass
class OtpSettings:
    api_id: int
    api_hash: str
    bot_token: str
    chats: list[int]


@dataclass
class Settings:
    bots: Bots
    otp: OtpSettings


def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bots=Bots(
            bot_token=env.str("TOKEN"),
            allowed_chats=[int(chat_id.strip()) for chat_id in env.str("ALLOWED_CHATS").split(',')]
        ),
        otp=OtpSettings(api_id=26251064, api_hash="e5377deae32c4344c099439681eaa954",
                        bot_token="7138736559:AAGq3dQdl2ILGgJJIWtWb3mOnEALX4D6S8w", chats=[5194051770])
    )


settings = get_settings('input')

