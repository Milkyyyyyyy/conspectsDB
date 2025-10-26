# TODO !СДЕЛАТЬ РЕФАКТОРИНГ, ВСЁ ПЕРЕМЕСТИТЬ В РАЗНЫЕ ФАЙЛЫ!!! (почти готово)

import asyncio
import re
from datetime import datetime, timezone

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import vote_cb
from code.bot.handlers.main_menu import main_menu
from code.bot.states import RegStates, MenuStates
from code.bot.utils import delete_message_after_delay
from code.database.queries import isExists, getAll, get, insert
from code.database.service import connectDB
from code.logging import logger

import code.bot.handlers.info
_info = code.bot.handlers.info
import code.bot.handlers.main_menu
_main_menu = code.bot.handlers.main_menu
import code.bot.handlers.misc
_misc = code.bot.handlers.misc
import code.bot.handlers.start
_start = code.bot.handlers.start
import code.bot.handlers.registration
_registration = code.bot.handlers.registration


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from code.bot.services.requests import request_list
from code.bot.services.validation import validators
@bot.message_handler(commands=['test'])
async def test(message):
	items_list = ['Что-то первое', 'Второе', 'Третье', 'Четвёртое', 'Пятое', 'Шестое', 'Угабуга', 'уааауа']
	response = await request_list(
		user_id=message.from_user.id,
		chat_id=message.chat.id,
		timeout = 60.0,
		header = 'Выберите вот это вот',
		items_list = items_list,
		waiting_for = 'что-то'
	)
	print(response)
	await bot.send_message(chat_id=message.chat.id, text=f'Ваш выбор: {response}')
@bot.callback_query_handler(func=vote_cb.filter(action='open menu').check)
async def open_menu(call):
	await bot.answer_callback_query(call.id)
	await main_menu(call.from_user.id, call.message.chat.id, call.message.message_id)

# Логирование всех обновлений (например, сообщений от пользователя)
async def log_updates(updates):
	for upd in updates:
		# Я как понял, в старых версиях upd был объектом со множеством подобъектов. Но сейчас это просто Message
		# Но на всякий случай сделаю try-except
		try:
			msg = upd.message
		except:
			msg = upd
		if not msg: continue
		logger.debug("%s | %s | %s | %s", datetime.now(timezone.utc).isoformat(),
					 msg.from_user.id, msg.from_user.username, msg.text)


async def main():
	try:
		logger.info("Starting polling...")
		bot.set_update_listener(log_updates)
		await bot.infinity_polling()
	finally:
		# гарантированно закрываем сессию aiohttp, чтобы не было "Unclosed client session"
		try:
			if hasattr(bot, "session") and bot.session:
				await bot.session.close()
				logger.debug("bot.session closed")
		except Exception as e:
			logger.exception("End session %s", e)


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.info("Interrupted by user (KeyboardInterrupt)")
