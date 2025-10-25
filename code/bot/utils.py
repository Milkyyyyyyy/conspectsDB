from code.logging import logger
from code.database.queries import connectDB, isExists
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from random import choice

# Удаляет сообщение через некоторое количество времени
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds=10):
	logger.debug(f'Delayed message deletion after {delay_seconds} seconds.')
	await asyncio.sleep(delay_seconds)
	try:
		await bot.delete_message(chat_id, message_id)
		logger.debug(f'Message {message_id} deleted')
	except Exception as e:
		logger.warning(f'Failed to delete message {message_id} in chat {chat_id}\n {e}')
		pass

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