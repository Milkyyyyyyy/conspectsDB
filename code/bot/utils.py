"""
Здесь различные утилиты для работы с ботом
"""

import asyncio
from datetime import datetime
from random import choice
from zoneinfo import ZoneInfo

from code.bot.bot_instance import bot
from code.logging import logger
import os
from telebot import types


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
		previous_message_id=None, chat_id=None, user_id=None, text='Не был введён текст', reply_markup=None):
	if chat_id is None or user_id is None:
		return
	try:
		if not previous_message_id is None:
			attempt = 0
			while attempt < 3:
				try:
					logger.debug("Trying to edit message (%s) text and markup...", previous_message_id)
					await bot.edit_message_text(text=text, chat_id=chat_id, message_id=previous_message_id,
					                            parse_mode='HTML')
					await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id,
					                                    reply_markup=reply_markup)
					return previous_message_id
				except:
					attempt += 1
					await asyncio.sleep(0.1)
				finally:
					logger.debug("Successfully edited message (%s) text and markup", previous_message_id)
					return
			logger.error("Can't edit message => just sending it")
			message = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup)
			return message.id
		else:
			logger.debug('There is no previous_message_id => just sending it')
			message = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup)
			return message.id
	except:
		logger.error("Unexpected error")
		return

async def send_message_with_files(
		chat_id,
		file_paths,
		files_text,
		markup_text=None,
		reply_markup=None
):
	"""
	:param chat_id: ID чата
	:param file_paths: Относительные пути до файлов
	:param files_text: Подпись под файлом или под медиа-группой (если файлов несколько)
	:markup_text: Сообщение, которое будет выводиться с reply_markup
	:reply_markup: markup сообщения
	"""

	# Если файлов нет - просто выводим сообщение с markup'ом
	if not file_paths:
		text = files_text
		if reply_markup:
			text += f'\n\n{reply_markup}'
		await bot.send_message(chat_id, text, reply_markup, parse_mode='HTML')
		return

	# Делаем объект итерируемым
	if isinstance(file_paths, str):
		file_paths = [file_paths, ]

	# Доступные расширения файлов фотографий
	image_extensions = ('.jpg', '.JPG', '.jpeg', '.png', '.gif', '.webp')

	photos = []
	documents = []

	# Разделяем file_paths на документы и файлы
	for path in file_paths:
		if not os.path.exists(path):
			logger.warning(f'File {path} does not exist')
			continue

		if path.lower().endswith(image_extensions):
			photos.append(path)
		else:
			documents.append(path)

	total_files = len(photos) + len(documents)

	# Если файлов суммарно больше одного, мы выводим медиа-группу
	if total_files > 1:
		media_group = []
		for i, photo_path in enumerate(photos):
			with open(photo_path, 'rb') as photo:
				caption = files_text if i == 0 else None
				media_group.append(types.InputMediaPhoto(photo.read(), caption=caption, parse_mode='HTML'))

		for i, doc_path in enumerate(documents):
			with open(doc_path, 'rb') as document:
				caption = files_text if len(photos) == 0 and i == 0 else None
				media_group.append(types.InputMediaDocument(document.read(), caption=caption, parse_mode='HTML'))
		message = await bot.send_media_group(chat_id, media_group)

	# Если документ или фото только одно, выводим одиночные файлы
	elif len(photos) == 1 and len(documents) == 0:
		with open(photos[0], 'rb') as photo:
			await bot.send_photo(chat_id, photo, caption=files_text, parse_mode='HTML')


	elif len(documents) == 1 and len(photos) == 0:
		with open(documents[0], 'rb') as document:
			await bot.send_document(chat_id, document, caption=files_text, parse_mode='HTML')

	# Если есть reply_markup, выводим отдельное сообщение с markup'ом
	if reply_markup and markup_text and not isinstance(reply_markup, types.ReplyKeyboardMarkup):
		await bot.send_message(chat_id, text=markup_text, reply_markup=reply_markup, parse_mode='HTML')






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
