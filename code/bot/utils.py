"""
Здесь различные утилиты для работы с ботом
"""

import asyncio
from datetime import datetime
from random import choice
from zoneinfo import ZoneInfo

from code.logging import logger

# TODO Поправить логи
# Удаляет сообщение через некоторое количество времени
async def delete_message_after_delay_interrupt(bot, chat_id, message_id, delay_seconds=10):
	logger.debug(f'Delayed message deletion after {delay_seconds} seconds.')
	await asyncio.sleep(delay_seconds)
	try:
		await bot.delete_message(chat_id, message_id)
		logger.debug(f'Message {message_id} deleted')
	except Exception as e:
		logger.warning(f'Failed to delete message {message_id} in chat {chat_id}\n {e}')
		pass
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds=10):
	asyncio.create_task(delete_message_after_delay_interrupt(bot, chat_id, message_id, delay_seconds))
async def send_temporary_message(bot, chat_id, text, delay_seconds=10):
	message = await bot.send_message(chat_id, text, parse_mode='HTML')
	asyncio.create_task(delete_message_after_delay_interrupt(bot=bot, chat_id=chat_id, message_id=message.message_id, delay_seconds=delay_seconds))
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
		greet = 'Доброй ночи.'
	phrases = ['С чего начнём?', 'Выберите нужную вам кнопку', 'Выберите действие ниже',
			   'Рад вас видеть.\nВыберите действие']
	return f'<b>{greet}!</b>\n\n{choice(phrases)}'
