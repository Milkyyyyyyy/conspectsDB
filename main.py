# TODO !СДЕЛАТЬ РЕФАКТОРИНГ, ВСЁ ПЕРЕМЕСТИТЬ В РАЗНЫЕ ФАЙЛЫ!!! (почти готово)

import asyncio
import re
from datetime import datetime, timezone

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.conspects import send_conspect_message
from code.bot.states import RegStates, MenuStates
from code.bot.utils import delete_message_after_delay
from code.database.queries import is_exists, get_all, get, insert
from code.database.service import connect_db
from code.logging import logger

import code.bot.handlers.main_menu
_main_menu = code.bot.handlers.main_menu
import code.bot.handlers.misc
_misc = code.bot.handlers.misc
import code.bot.handlers.start
_start = code.bot.handlers.start
import code.bot.handlers.registration
_registration = code.bot.handlers.registration
import code.bot.handlers.conspects_menu
_conspect_menu = code.bot.handlers.conspects_menu
import code.bot.handlers.admin_menu
_admin_menu = code.bot.handlers.admin_menu
import code.bot.handlers.conspect_load
_conspect_load = code.bot.handlers.conspect_load
import code.bot.handlers.user_conspects
_user_conspects = code.bot.handlers.user_conspects
import code.bot.handlers.conspects_searching
_conspects_searching = code.bot.handlers.conspects_searching


from code.bot.utils import send_message_with_files


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from code.bot.services.requests import request_list, request_confirmation, request_files
from code.bot.services.validation import validators

from code.database.service import connect_db
from code.database.queries import get_all

from code.bot.services.files import hard_cleaning
@bot.message_handler(commands=['test'])
async def test(message):
	async with connect_db() as db:
		conspects = await get_all(
			database=db,
			table='CONSPECTS',
			filters = {
				'status': ['pending', 'NOT']
			}
		)
		for conspect in conspects:
			await send_conspect_message(
				message.from_user.id,
				message.chat.id,
				conspect_id=conspect['rowid']
			)

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
	await hard_cleaning()
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
