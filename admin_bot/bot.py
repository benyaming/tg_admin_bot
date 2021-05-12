import logging
from os import environ
from typing import Tuple
from asyncio import sleep, create_task

from aiogram import Dispatcher, Bot
from aiogram.utils.executor import start_polling
from aiogram.types import (
    ContentTypes,
    Message,
    CallbackQuery
)
from betterlogging import get_colorized_logger, DEBUG

from admin_bot.utils import *
from admin_bot.config_parser import CONFIG_STORAGE


logger = get_colorized_logger('admin_bot')
logger.setLevel(DEBUG)

STORAGE = {}
ATTEMPTS = []
TIME_TO_CHECK = int(environ.get('TIME_TO_CHECK', 300))


bot = Bot(environ.get('TOKEN'))
dp = Dispatcher(bot)


async def on_start(dispatcher: Dispatcher):
    logger.info('STARTING TELEGRAM ADMIN BOT...')
    logger.info(f'Time to check: {TIME_TO_CHECK}')


async def on_shutdown(dispatcher: Dispatcher):
    for token in STORAGE:
        await stop_user_track(token)


async def stop_user_track(token: Tuple[int, int], kick: int = False):
    user_id, chat_id = token
    msg_id, service_msg_id = STORAGE[token]
    logger.info(f'Stop user track for user {user_id}')

    if kick:
        logger.info(f'Kicking user {user_id}')
        await bot.kick_chat_member(chat_id, user_id)
        await bot.delete_message(chat_id, service_msg_id)
    else:
        logger.info(f'Grant allow permissions to user {user_id}')
        await bot.restrict_chat_member(chat_id, user_id, permissions=ALLOW_PERMISSIONS)

    logger.info(f'Deleting token {token} from storage.')

    if token in ATTEMPTS:
        ATTEMPTS.remove(token)
    del STORAGE[token]

    logger.info(f'Deletting message {msg_id}')
    await bot.delete_message(chat_id, msg_id)


async def init_user_track(user_id: int, chat_id: int, msg_id: int, service_msg_id: int):
    token = (user_id, chat_id)
    STORAGE[token] = (msg_id, service_msg_id)

    await sleep(TIME_TO_CHECK)

    if token in STORAGE:
        await stop_user_track(token, kick=True)


def validate_attempt(token: Tuple[int, int]) -> bool:
    if token in ATTEMPTS:
        return False

    ATTEMPTS.append(token)
    return True


@dp.message_handler(commands=['start'])
async def handle_start(msg: Message):
    if msg.chat.type == 'private':
        await msg.reply('Hi!')


@dp.message_handler(content_types=ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(msg: Message):
    config = CONFIG_STORAGE.get(msg.chat.mention.lower())
    if not config:
        return

    if len(msg.new_chat_members) > 0 and msg.new_chat_members[0].id != msg.from_user.id:
        logger.info(f'User {msg.from_user.id} added user {msg.new_chat_members[0].id}. Skipping...')
        return

    logger.info(f'New chat_member detected! id: {msg.from_user.id}. Restricting...')
    await bot.restrict_chat_member(msg.chat.id, msg.new_chat_members[0].id, permissions=RESTRICT_PERMISSIONS)

    kb = get_keyboard(msg.from_user.id, config.button_options)

    answer = await msg.reply(config.question, reply_markup=kb)
    create_task(init_user_track(
        user_id=msg.from_user.id,
        chat_id=msg.chat.id,
        msg_id=answer.message_id,
        service_msg_id=msg.message_id
    ))


@dp.message_handler(content_types=ContentTypes.LEFT_CHAT_MEMBER)
async def handle_left_member(msg: Message):
    logger.info(f'User {msg.from_user.id} left the group {msg.chat.id}')
    token = (msg.from_user.id, msg.chat.id)
    if token in STORAGE:
        logger.info(f'Removing token {token} from storage')
        await stop_user_track(token)


@dp.callback_query_handler(lambda call: True)
async def handle_button(call: CallbackQuery):
    config = CONFIG_STORAGE.get(call.message.chat.mention.lower())
    if not config:
        return

    user_id, answer = call.data.split(':')

    if call.from_user.id == int(user_id):
        if answer != config.right_answer:
            allow_attempt = validate_attempt((call.from_user.id, call.message.chat.id))
            logger.debug(f'{call.from_user.id} entered wrong value [{answer}]!')

            if allow_attempt:
                await bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=get_keyboard(call.from_user.id, config.button_options)
                )
                await call.answer(config.answer_wrong_button, show_alert=True)
                return
            else:
                return await stop_user_track((call.from_user.id, call.message.chat.id), kick=True)
        await call.answer(config.answer_right_button)
        logger.info(f'{call.from_user.id} passed the test! Removing restrictions...')

        token = (call.from_user.id, call.message.chat.id)
        await stop_user_track(token)
        logger.info(f'{call.from_user.id} allowed to chat!')

    else:
        if config.is_wrong_numbers_enabled:
            answer = random.choice(config.wrong_answers)
        else:
            answer = "Forbidden!"

        await call.answer(answer, show_alert=True)


if __name__ == '__main__':
    start_polling(dp, skip_updates=True, on_startup=on_start, on_shutdown=on_shutdown)
    dp.stop_polling()
