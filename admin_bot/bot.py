import logging
from os import environ
from asyncio import sleep, create_task

from aioredis import create_redis
from aiogram import Dispatcher, Bot
from aiogram.utils.executor import start_polling
from aiogram.types import  (
    ContentTypes,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
    CallbackQuery
)

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s [ %(levelname)s ] <|> %(message)s')


question_text = 'Добро пожаловать! У вас есть 5 минут чтобы доказать, что вы не спамер!'
button_text = 'Я не спамер!'
answer_query_right_user = 'Добро пожаловать!'
answer_query_wrong_user = 'Эта кнопка не для тебя!'
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
CONNECTORS = {
    'redis': None
}

bot = Bot(environ.get('TOKEN'))
dp = Dispatcher(bot)


async def on_start(dispatcher: Dispatcher):
    logging.info('STARTING TELEGRAM ADMIN BOT...')
    CONNECTORS['redis'] = await create_redis(
        address=f'redis://{environ.get("REDIS_HOST")}:{environ.get("REDIS_PORT")}',
        db=int(environ.get('REDIS_DB'))
    )


async def on_shutdown(dispatcher: Dispatcher):
    if CONNECTORS['redis']:
        await CONNECTORS['redis'].flushdb()
        logging.info('DB FLUSHED')
    logging.info('SHUTDOWN...')


async def init_user_track(user_token: str):
    await CONNECTORS['redis'].set(user_token, 1)

    await sleep(300)
    user_in_redis = await CONNECTORS['redis'].exists(user_token)
    if not bool(user_in_redis):
        return
    user, chat, msg_id = user_token.split(':')
    await bot.kick_chat_member(chat, user)
    await CONNECTORS['redis'].delete(user_token)
    await bot.delete_message(chat, msg_id)


async def stop_user_track(user_token: str):
    logging.info(f'Deleting token {user_token} from redis.')
    CONNECTORS['redis'].delete(user_token)


@dp.message_handler(content_types=ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(msg: Message):
    logging.info(f'New chat_member detected! id: {msg.from_user.id}. Restricting...')
    await bot.restrict_chat_member(msg.chat.id, msg.new_chat_members[0].id, permissions=RESTRICT_PERMISSIONS)
    logging.info(f'Restricted! id: {msg.from_user.id}')
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
        logging.info(f'{call.from_user.id} passed the test! Removing restrictions...')
        answer = answer_query_right_user
        await bot.restrict_chat_member(chat_id, user, permissions=ALLOW_PERMISSIONS)
        await bot.delete_message(chat_id, msg_id)
    else:
        answer = answer_query_wrong_user
    await call.answer(answer)
    await stop_user_track(f'{call.from_user.id}:{call.message.chat.id}')
    logging.info(f'{call.from_user.id} allowed to chat!')


if __name__ == '__main__':
    start_polling(dp, skip_updates=True, on_startup=on_start, on_shutdown=on_shutdown)
