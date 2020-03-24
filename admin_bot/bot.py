import logging
import random
from os import environ
from asyncio import sleep, create_task

from aiogram import Dispatcher, Bot
from aiogram.utils.executor import start_polling
from aiogram.types import (
    ContentTypes,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)

from admin_bot.utils import *


logging.basicConfig(level=logging.INFO, format='%(asctime)-15s [ %(levelname)s ] <|> %(message)s')

STORAGE = {}


bot = Bot(environ.get('TOKEN'))
dp = Dispatcher(bot)


async def on_start(dispatcher: Dispatcher):
    logging.info('STARTING TELEGRAM ADMIN BOT...')


async def on_shutdown(dispatcher: Dispatcher):
    for token in STORAGE:
        await stop_user_track(token)


async def stop_user_track(token: tuple, kick: int = False):
    user_id, chat_id = token
    msg_id = STORAGE[token]
    logging.info(f'Stop user track for user {user_id}')

    if kick:
        logging.info(f'Kicking user {user_id}')
        await bot.kick_chat_member(chat_id, user_id)
    else:
        logging.info(f'Grant allow permissions to user {user_id}')
        await bot.restrict_chat_member(chat_id, user_id, permissions=ALLOW_PERMISSIONS)

    logging.info(f'Deleting token {token} from storage.')
    del STORAGE[token]

    logging.info(f'Deletting message {msg_id}')
    await bot.delete_message(chat_id, msg_id)


async def init_user_track(user_id: int, chat_id: int, msg_id: int):
    token = (user_id, chat_id)
    STORAGE[token] = msg_id

    await sleep(300)

    if token in STORAGE:
        await stop_user_track(token, kick=True)


@dp.message_handler(commands=['start'])
async def handle_start(msg: Message):
    await msg.reply('Hi!')


# @dp.message_handler(commands=['q'])
# async def q(msg: Message):
#     await on_shutdown('d')


@dp.message_handler(content_types=ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(msg: Message):
    if len(msg.new_chat_members) > 0 and msg.new_chat_members[0].id != msg.from_user.id:
        logging.info(f'User {msg.from_user.id} added user {msg.new_chat_members[0].id}. Skipping...')
        return

    logging.info(f'New chat_member detected! id: {msg.from_user.id}. Restricting...')
    await bot.restrict_chat_member(msg.chat.id, msg.new_chat_members[0].id, permissions=RESTRICT_PERMISSIONS)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(button_text, callback_data=msg.from_user.id))

    answer = await bot.send_message(msg.chat.id, question_text, reply_markup=kb)
    create_task(init_user_track(
        user_id=msg.from_user.id,
        chat_id=msg.chat.id,
        msg_id=answer.message_id
    ))


@dp.message_handler(content_types=ContentTypes.LEFT_CHAT_MEMBER)
async def handle_left_member(msg: Message):
    logging.info(f'User {msg.from_user.id} left the group {msg.chat.id}')
    token = (msg.from_user.id, msg.chat.id)
    if token in STORAGE:
        logging.info(f'Removing token {token} from storage')
        await stop_user_track(token)


@dp.callback_query_handler(lambda call: True)
async def handle_button(call: CallbackQuery):
    user_id = int(call.data)

    if call.from_user.id == user_id:
        await call.answer(answer_query_right_user)
        logging.info(f'{call.from_user.id} passed the test! Removing restrictions...')

        token = (call.from_user.id, call.message.chat.id)
        await stop_user_track(token)
        logging.info(f'{call.from_user.id} allowed to chat!')

    else:
        answer = random.choice(wrong_answers)
        await call.answer(answer, show_alert=True)


if __name__ == '__main__':
    start_polling(dp, skip_updates=True, on_startup=on_start, on_shutdown=on_shutdown)
    dp.stop_polling()
