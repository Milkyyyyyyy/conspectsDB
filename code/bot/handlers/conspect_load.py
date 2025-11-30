from datetime import datetime
from zoneinfo import ZoneInfo

from aiosqlite import connect
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.files import save_files, delete_files
from code.bot.services.requests import (request, request_list, request_confirmation, request_files,
										wait_for_callback_on_message)
from code.bot.services.validation import validators
from code.bot.utils import send_temporary_message, send_message_with_files
from code.database.queries import get_all, get, insert
from code.database.service import connect_db
from code.logging import logger
from code.utils import normalize_keywords
import asyncio
import os
from typing import Optional, Tuple, List, Union
from code.utils import normalize_paths

# Константы в начале модуля
MAX_FILE_UPLOAD_ATTEMPTS = 5
TIMEZONE = 'Europe/Ulyanovsk'
CONSPECT_FILES_DIR = os.getenv('CONSPECT_FILES_DIR', 'files/conspect_files')


@bot.callback_query_handler(func=call_factory.filter(area='conspects_upload').check)
async def callback_handler(call):
	logger.debug('Handle callback in creation...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', user_id, exc_info=e)

	action = call_factory.parse(callback_data=call.data)['action']

	if action == 'upload_conspect':  # Заменить match-case для Python <3.10
		await create_conspect(user_id=user_id, chat_id=chat_id)
		try:
			await bot.delete_message(chat_id=chat_id, message_id=message_id)
		except Exception as e:  # Явно указать Exception
			logger.warning(f"Can't delete message {message_id}: {e}")


async def create_conspect(
		message=None,
		user_id: Optional[int] = None,
		chat_id: Optional[int] = None
) -> None:
	"""Создание конспекта с обработкой ошибок и очисткой ресурсов."""
	if user_id is None:
		user_id = message.from_user.id
	if chat_id is None:
		chat_id = message.chat.id

	file_paths: List[str] = []
	error_occurred = False

	try:
		# Получение предмета
		subject_id, subject_name = await _get_subject_selection(user_id, chat_id)

		# Загрузка файлов с повторными попытками
		files = await _request_files_with_retry(user_id, chat_id, MAX_FILE_UPLOAD_ATTEMPTS)
		if files is None:
			asyncio.create_task(main_menu(user_id, chat_id))
			return
		file_paths = await save_files(files, save_dir=CONSPECT_FILES_DIR)
		file_paths = await normalize_paths(file_paths)

		# Сбор метаданных
		theme, conspect_date, keywords = await _collect_conspect_metadata(user_id, chat_id)

		upload_date = datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M:%S %d.%m.%Y")  # Исправлен формат

		await accept_creation(
			user_id=user_id,
			chat_id=chat_id,
			subject_id=subject_id,
			subject_name=subject_name,
			theme=theme,
			keywords=keywords,
			conspect_date=conspect_date,
			upload_date=upload_date,
			file_paths=file_paths
		)

	except Exception as e:
		error_occurred = True
		logger.exception("Unexpected error during conspect creation", exc_info=e)
		await send_temporary_message(chat_id, 'Произошла ошибка. Попробуйте ещё раз.', delay_seconds=10)
	finally:
		# Всегда очищаем файлы при ошибке (если не были сохранены в БД)
		if file_paths and error_occurred:
			try:
				await delete_files(file_paths)
			except Exception as cleanup_error:
				logger.error(f"Failed to delete files: {cleanup_error}")

async def stop_creation(chat_id, user_id, file_paths=None):
	logger.info("stop_creation called", extra={"chat_id": chat_id})
	await send_temporary_message(chat_id, 'Завершаю создание конспекта...', delay_seconds=10)
	if file_paths:
		try:
			await delete_files(file_paths)
		except Exception as cleanup_error:
			logger.error(f"Failed to delete files: {cleanup_error}")
	asyncio.create_task(main_menu(user_id, chat_id))
	return
async def _collect_conspect_metadata(user_id, chat_id):
	theme, _ = await request_theme(user_id, chat_id)
	if theme is None:
		logger.info("Theme request returned None — stopping creation conspect", extra={"user_id": user_id})
		await stop_creation(chat_id, user_id)
		return
	conspect_date, _ = await request_date(user_id, chat_id)
	if conspect_date is None:
		logger.info("Surname request returned None — stopping conspect", extra={"user_id": user_id})
		await stop_creation(chat_id, user_id)
		return

	keywords, _ = await request_keywords(user_id, chat_id)
	return theme, conspect_date, keywords
async def _get_subject_selection(user_id, chat_id):
	async with connect_db() as db:
		# Узнаём, какие предметы относятся к направлению пользователя
		user = await get(database=db, table='USERS', filters={'telegram_id': user_id})
		user_direction_id = user['direction_id']
		all_subjects_by_direction = await get_all(
			database=db,
			table='SUBJECT_DIRECTIONS',
			filters={'direction_id': user_direction_id}
		)
		# Собираем фильтр из всех подходящих предметов
		subject_filters = {'rowid': []}
		for subject in all_subjects_by_direction:
			subject_filters['rowid'].append(subject['subject_id'])
		if len(subject_filters['rowid']) == 0:
			await send_temporary_message(chat_id, text='<b>Не удалось найти предметы.</b>\n'
													   'Обратитесь к модерации или поменяйте факультет/кафедру/направление в меню "О пользователе"')
			await main_menu(user_id, chat_id)
			return
		# Получаем все предметы из датабазы
		all_subjects = await get_all(
			database=db,
			table='SUBJECTS',
			filters=subject_filters,
			operator='OR'
		)
	subject_id, subject_name = await request_list(
		user_id=user_id,
		chat_id=chat_id,
		header='Выберите предмет',
		items_list=all_subjects,
		input_field='name',
		output_field=['rowid', 'name']
	)
	return subject_id, subject_name

async def _request_files_with_retry(
		user_id: int,
		chat_id: int,
		max_attempts: int,
		request_message: str = 'Отправьте файлы конспекта (фото или документ) и нажмите "подтвердить"'
) -> Union[List, None]:
	"""Запрос файлов с повторными попытками."""
	for attempt in range(1, max_attempts + 1):
		files = await request_files(
			user_id=user_id,
			chat_id=chat_id,
			request_message=request_message
		)
		if files == 'cancel':
			return None
		if files:
			return files

		if attempt >= max_attempts:
			raise ValueError("Превышено количество попыток загрузки файлов")

		await send_temporary_message(
			chat_id,
			'Вы не приложили ни одного файла.\nПовторите попытку'
		)
		await asyncio.sleep(0.3)

	return []  # Недостижимо, но для type checker


# Исправленные кнопки в accept_creation

async def get_conspect_info_text(subject_name, theme, conspect_date, keywords):
	conspect_info = (f"<blockquote><b>📖 Предмет: </b> {subject_name}\n"
	                 f"<b>📝 Тема: </b> {theme}\n"
	                 f"<b>📅 Дата конспекта: </b> {conspect_date}\n"
	                 f"<b>🔍 Ключевые слова: </b> {keywords}</blockquote>\n")
	return conspect_info
async def request_theme(user_id, chat_id,
                        request_message='Введите тему текущего конспекта:'):
	theme, message_id = await request(
		user_id=user_id,
		chat_id=chat_id,
		request_message=request_message,
		validator=validators.theme
	)
	return theme, message_id
async def request_date(user_id, chat_id,
                       request_message='Введите дату текущего конспекта в формате ДД.ММ.ГГГГ\n'
                                       'Если не знаете - напишите текущую дату):'):
	date, message_id = await request(
		user_id=user_id,
		chat_id=chat_id,
		request_message=request_message,
		validator=validators.conspect_date
	)
	return date, message_id
async def request_keywords(user_id, chat_id,
                           request_message = 'Введите ключевые слова для поиска через пробел или запятую.\n'
		                'Это очень поможет пользователям найти ваш конспект.'):
	keywords, message_id = await request(
		user_id=user_id,
		chat_id=chat_id,
		request_message=request_message

	)
	keywords = await normalize_keywords(keywords)
	return keywords, message_id
async def accept_creation(
		user_id=None,
		chat_id=None,
		subject_id=None,
		subject_name=None,
		keywords=None,
		theme=None,
		conspect_date=None,
		upload_date=None,
		file_paths=None

):
	logger.debug("Presenting registration confirmation to user",
				 extra={"user_id": user_id, "chat_id": chat_id,
						"theme": theme, "conspect_date": conspect_date, "upload_date": upload_date})
	try:
		''' TODO Здесь нужно поменять request_confirmation на такую структуру:
		Мы создаём сообщение, в котором выводим всю нужную информацию
		А в markup (кнопки) добавляем кнопки типа:
		- Изменить тему
		- Выбрать другой предмет
		- ...

		Это всё поместим в while callback_data != 'accepted' или там подобное
		Затем с помощью функции wait_for_callback мы будем ожидать от пользователя нажатие кнопки
		  И эта функция (wait_for_callback) вернёт нам callback_data, и в зависимости от этой информации
		мы будем предоставлять пользователю возможность на этом этапе заменить всю информацию
		'''


		accept_button = InlineKeyboardButton('✅ Да', callback_data='True')
		decline_button = InlineKeyboardButton('❌ Нет', callback_data='False')
		change_files_button = InlineKeyboardButton('Прикрепить другие файлы', callback_data='change_files')
		change_theme_button = InlineKeyboardButton('Изменить тему', callback_data='change_theme')
		change_date_button = InlineKeyboardButton('Изменить дату', callback_data='change_date')
		change_keywords_button = InlineKeyboardButton('Изменить теги', callback_data='change_keywords')
		markup = InlineKeyboardMarkup()
		markup.row(change_files_button)
		markup.row(change_theme_button, change_date_button, change_keywords_button)
		markup.row(accept_button, decline_button)

		response = ''
		while not response in ('True', 'False', 'None'):
			conspect_info = await get_conspect_info_text(subject_name, theme, conspect_date, keywords)
			message = await send_message_with_files(
				chat_id=chat_id,
				files_text=conspect_info,
				file_paths=file_paths,
				markup_text='Выберите действие:',
				reply_markup=markup
			)
			response = await wait_for_callback_on_message(
				user_id=user_id,
				chat_id=chat_id,
				message_id=message.id
			)
			match response:
				case ('True', 'False'):
					break
				case 'change_files':
					new_files = await _request_files_with_retry(user_id, chat_id, 3,
					                                      request_message='Добавьте новые файлы и нажмите "подтвердить"')
					if new_files is None:
						continue
					new_file_paths = await save_files(new_files, 'files/conspect_files')
					await delete_files(file_paths)
					file_paths = new_file_paths
				case 'change_theme':
					new_theme, _ = await request_theme(user_id, chat_id, request_message='Введите новую тему')
					theme = new_theme
				case 'change_date':
					new_date, _ = await request_date(user_id, chat_id, request_message='Введите новую дату')
					conspect_date = new_date
				case 'change_keywords':
					new_keywords, _ = await request_keywords(user_id, chat_id, request_message='Введите новые теги')
					keywords = new_keywords
	except Exception as e:
		logger.exception("Error while asking for creation confirmation", exc_info=e)
		await send_temporary_message(chat_id, text='Произошла ошибка. Повторите позже.', delay_seconds=5)
		await stop_creation(chat_id, user_id, file_paths)
		return
	if response == 'False':
		logger.info("User cancelled at confirmation step", extra={"user_id": user_id})
		await stop_creation(chat_id, user_id, file_paths)
		return

	keywords_str = ", ".join(keywords.split(' '))
	if response == 'True':
		logger.info("User accepted registration — proceeding to save", extra={"user_id": user_id})
		await end_creation(
			user_id=user_id,
			chat_id=chat_id,
			subject_id=subject_id,
			keywords=keywords_str,
			theme=theme,
			conspect_date=conspect_date,
			upload_date=upload_date,
			file_paths=file_paths
		)
	else:
		logger.info("User requested to repeat registration", extra={"user_id": user_id})
		await create_conspect(user_id=user_id, chat_id=chat_id)
		return
async def end_creation(
		user_id=None,
		chat_id=None,
		subject_id=None,
		keywords=None,
		theme=None,
		conspect_date=None,
		upload_date=None,
		file_paths=None
):
	error_occurred = False
	try:
		async with connect_db() as db:
			conspect_id, _ = await insert(
				database=db,
				table='CONSPECTS',
				filters={
					'subject_id': subject_id,
					'upload_date': upload_date,
					'conspect_date': conspect_date,
					'theme': theme,
					'user_telegram_id': user_id,
					'keywords': keywords,
					'views': 0,
					'status': 'pending',
					'rating': 0,
					'anonymous' : False
				}
			)
			for path in file_paths:
				await insert(
					database=db,
					table='CONSPECTS_FILES',
					filters = {
						'conspect_id': conspect_id,
						'path': path
					}

				)
	except Exception as e:
		error_occurred = True
		logger.exception(f'Error while adding conspect info in database {e}')
	finally:
		if error_occurred:
			await bot.send_message(chat_id, 'Произошла ошибка при загрузке конспекта!')
			await stop_creation(chat_id, user_id, file_paths)
		else:
			await bot.send_message(chat_id, 'Конспект успешно загружен в датабазу')
			await asyncio.sleep(0.5)
			asyncio.create_task(main_menu(user_id, chat_id))
		return
