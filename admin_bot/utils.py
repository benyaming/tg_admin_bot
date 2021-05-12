import random

import yaml
from aiogram.types.chat_permissions import ChatPermissions
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_yaml() -> dict:
    with open('../config.yaml', encoding='utf-8') as f:
        return yaml.load(f, Loader=yaml.Loader)


config = get_yaml()
question_text = config['question']

button_options = [a['title'] for a in config['button_options']]
right_button_text = list(filter(lambda a: a['correct'], config['button_options']))[0]['title']

answer_query_wrong_button = 'Неверно, осталась одна попытка.'
answer_query_right_user = 'Добро пожаловать!'

wrong_answers = config['wrong_answers'] if config['enable_wrong_answers'] else ['Недоступно']

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


def get_keyboard(user_id: int) -> InlineKeyboardMarkup:
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
