from os import environ

from aiogram import Dispatcher, Bot
from aiogram.utils.executor import start_polling
from aiogram.types import ContentTypes, Message, InlineKeyboardButton, \
    InlineKeyboardMarkup, ChatPermissions, CallbackQuery


question_text = 'А не спамер ли ты?'
button_text = 'Я не спамер!'
answer_query_right_user = 'Добро пожаловать'
answer_query_wrong_user = 'Эта кнопка не для тебя!'

bot = Bot('908972444:AAFpq6Odobjf_DaX4zHfwCx00RQH4M1SQ6c')
dp = Dispatcher(bot)


@dp.message_handler(content_types=ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(msg: Message):
    rights = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False
    )
    await bot.restrict_chat_member(msg.chat.id, msg.from_user.id, permissions=rights)

    answer = await bot.send_message(msg.chat.id, question_text)

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


start_polling(dp)
