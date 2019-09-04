from os import environ
from asyncio import sleep, create_task

from aioredis import create_redis
from aiogram import Dispatcher, Bot
from aiogram.utils.executor import start_polling
from aiogram.types import ContentTypes, Message, InlineKeyboardButton, \
    InlineKeyboardMarkup, ChatPermissions, CallbackQuery


question_text = 'Добро пожаловать! У вас есть 5 минут чтобы доказать, что вы не спамер!'
button_text = 'Я не спамер!'
answer_query_right_user = 'Добро пожаловать!'
answer_query_wrong_user = 'Эта кнопка не для тебя!'

bot = Bot(environ.get('TOKEN'))
dp = Dispatcher(bot)


async def init_user_track(user_token: str) -> None:
    redis = await create_redis(
        f'redis://{environ.get("REDIS_HOST")}:{environ.get("REDIS_PORT")}'
    )
    await redis.set(user_token, 1)

    await sleep(300)
    user_in_redis = await redis.exists(user_token)
    if not bool(user_in_redis):
        return
    user, chat, msg_id = user_token.split(':')
    await bot.kick_chat_member(chat, user)
    await redis.delete(user_token)
    await bot.delete_message(chat, msg_id)


async def stop_user_track(user_token: str) -> None:
    redis = await create_redis(
        f'redis://{environ.get("REDIS_HOST")}:{environ.get("REDIS_PORT")}'
    )
    redis.delete(user_token)


@dp.message_handler(content_types=ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(msg: Message):
    rights = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False
    )
    await bot.restrict_chat_member(msg.chat.id, msg.new_chat_members[0].id, permissions=rights)
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

    rights = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True
    )

    if call.from_user.id == user:
        answer = answer_query_right_user
        await bot.restrict_chat_member(chat_id, user, permissions=rights)
        await bot.delete_message(chat_id, msg_id)
    else:
        answer = answer_query_wrong_user
    await call.answer(answer)
    await stop_user_track(f'{call.from_user.id}:{call.message.chat.id}')


start_polling(dp, skip_updates=True)
