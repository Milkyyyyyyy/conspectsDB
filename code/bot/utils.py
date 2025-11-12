"""
Здесь различные утилиты для работы с ботом
"""

import asyncio
from datetime import datetime
from random import choice
from zoneinfo import ZoneInfo

from code.logging import logger
from code.bot.bot_instance import bot


# TODO Поправить логи
async def delete_message_after_delay_interrupt(chat_id, message_id, delay_seconds=10):
	"""
	Удаляет сообщение через указанное время (с возможностью прерывания)
	"""
	if bot is None:
		logger.error('Bot instance is None')
		return
	if not isinstance(chat_id, (int, str)) or not message_id:
		logger.warning('Invalid chat_id or message_id', extra={"chat_id": chat_id, "message_id": message_id})
		return
	try:
		delay_seconds = max(0, int(delay_seconds))
	except Exception:
		logger.warning('Invalid delay_seconds=%r, fallback to 10 sec.', delay_seconds)
		delay_seconds = 10

	logger.debug(f"Scheduling deletion of message {message_id} after {delay_seconds}s",
	             extra={"chat_id": chat_id, "message_id": message_id})
	try:
		await asyncio.sleep(delay_seconds)
	except asyncio.CancelledError:
		logger.info("Deletion task for message %s cancelled", message_id, extra={"chat_id": chat_id})
		return
	except Exception:
		logger.exception("Unexpected error during sleep before deletion",
		                 extra={"chat_id": chat_id, "message_id": message_id})

	try:
		await bot.delete_message(chat_id, message_id)
		logger.info(f"Message {message_id} deleted successfully", extra={"chat_id": chat_id, "message_id": message_id})
	except Exception as e:
		logger.warning(f"Failed to delete message {message_id} in chat {chat_id}: {e}",
		               extra={"chat_id": chat_id, "message_id": message_id})


async def delete_message_after_delay(chat_id, message_id, delay_seconds=10):
	asyncio.create_task(delete_message_after_delay_interrupt(chat_id, message_id, delay_seconds))


async def send_temporary_message(chat_id, text, delay_seconds=10):
	message = await bot.send_message(chat_id, text, parse_mode='HTML')
	asyncio.create_task(delete_message_after_delay_interrupt(chat_id=chat_id, message_id=message.message_id,
	                                                         delay_seconds=delay_seconds))

async def safe_edit_message(
		previous_message_id=None,
		chat_id=None,
		user_id=None,
		text='Не был введён текст',
		reply_markup=None
):
	if chat_id is None or user_id is None:
		return
	try:
		if not previous_message_id is None:
			try:
				logger.debug("Trying to edit message (%s) text and markup...", previous_message_id)
				await bot.edit_message_text(text=text, chat_id=chat_id, message_id=previous_message_id, parse_mode='HTML')
				await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=reply_markup)
			except:
				logger.error("Can't edit message => just sending it")
				await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup)
			finally:
				logger.debug("Successfully edited message (%s) text and markup", previous_message_id)
		else:
			logger.debug('There is no previous_message_id => just sending it')
			await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup)
	except:
		logger.error("Unexpected error")
		return

async def get_greeting():
	now = datetime.now(ZoneInfo('Europe/Ulyanovsk'))
	hour = now.hour
	if 5 <= hour < 12:
		greet = 'Доброе утро'
	elif 12 <= hour < 18:
		greet = 'Добрый день'
	elif 18 <= hour < 23:
		greet = 'Добрый вечер'
	else:
		greet = 'Доброй ночи'
	phrases = ['С чего начнём?', 'Выберите нужную вам кнопку', 'Выберите действие ниже',
	           'Рад вас видеть.\nВыберите действие']
	return f'<b>{greet}!</b>\n\n{choice(phrases)}'
