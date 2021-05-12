import random
from typing import List

from aiogram.types.chat_permissions import ChatPermissions
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


RESTRICT_PERMISSIONS = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False
    )
ALLOW_PERMISSIONS = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True
    )


def get_keyboard(user_id: int, button_options: List[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row_width = 5

    random.shuffle(button_options)

    buttons = []

    for answer in button_options:
        buttons.append(InlineKeyboardButton(
            text=answer,
            callback_data=f'{user_id}:{answer}'
        ))
    kb.add(*buttons)

    return kb
