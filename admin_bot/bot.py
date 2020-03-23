import logging
import random
from os import environ
from typing import Dict, Optional, List
from asyncio import sleep, create_task

from aioredis import create_redis, Redis
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

CONNECTORS: Dict[str, Optional[Redis]] = {
    'redis': None
}


bot = Bot(environ.get('TOKEN'))
dp = Dispatcher(bot)


async def flush_db():
    keys: List[bytes] = await CONNECTORS['redis'].keys('*')
    for token in keys:
        await stop_user_track(token.decode('utf-8'))
    await CONNECTORS['redis'].flushdb()


async def on_start(dispatcher: Dispatcher):
    logging.info('STARTING TELEGRAM ADMIN BOT...')
    CONNECTORS['redis'] = await create_redis(
        address=f'redis://{environ.get("REDIS_HOST")}:{environ.get("REDIS_PORT")}',
        db=int(environ.get('REDIS_DB'))
    )


async def on_shutdown(dispatcher: Dispatcher):
    if CONNECTORS['redis']:
        await flush_db()
        logging.info('DB FLUSHED')
    logging.info('SHUTDOWN...')


async def stop_user_track(user_token: str, kick: int = False):
    logging.info(f'Stop user track for {user_token}')
    user_id, chat_id, msg_id = map(int, user_token.split(':'))

    if kick:
        logging.info(f'Kicking user {user_id}')
        await bot.kick_chat_member(chat_id, user_id)
    else:
        logging.info(f'Grant allow permissions to user {user_id}')
        await bot.restrict_chat_member(chat_id, user_id, permissions=ALLOW_PERMISSIONS)

    logging.info(f'Deleting token {user_token} from redis.')
    await CONNECTORS['redis'].delete(user_token)

    logging.info(f'Deletting message {msg_id}')
    await bot.delete_message(chat_id, msg_id)


async def init_user_track(user_token: str):
    await CONNECTORS['redis'].set(user_token, 1)

    await sleep(300)
    user_in_redis = await CONNECTORS['redis'].exists(user_token)
    if not bool(user_in_redis):
        return

    await stop_user_track(user_token, kick=True)


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

    answer = await bot.send_message(msg.chat.id, question_text)
    create_task(init_user_track(f'{msg.from_user.id}:{msg.chat.id}:{answer.message_id}'))

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(
        button_text,
        callback_data=f'{msg.chat.id}:{msg.from_user.id}:{answer.message_id}')
    )
    await bot.edit_message_reply_markup(msg.chat.id, answer.message_id, reply_markup=kb)


@dp.callback_query_handler(lambda call: True)
async def handle_button(call: CallbackQuery):
    chat_id, user, msg_id = map(int, call.data.split(':'))

    if call.from_user.id == user:
        await call.answer(answer_query_right_user)
        logging.info(f'{call.from_user.id} passed the test! Removing restrictions...')

        await stop_user_track(f'{call.from_user.id}:{call.message.chat.id}:{msg_id}')
        logging.info(f'{call.from_user.id} allowed to chat!')

    else:
        answer = random.choice(wrong_answers)
        await call.answer(answer, show_alert=True)


if __name__ == '__main__':
    start_polling(dp, skip_updates=True, on_startup=on_start, on_shutdown=on_shutdown)
    dp.stop_polling()
