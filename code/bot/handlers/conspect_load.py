from datetime import datetime
from zoneinfo import ZoneInfo

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.files import save_files, delete_files
from code.bot.services.requests import (request, request_list, request_confirmation, request_files,
                                        wait_for_callback_on_message)
from code.bot.services.validation import validators
from code.bot.utils import send_temporary_message, send_message_with_files
from code.database.queries import get_all, get
from code.database.service import connect_db
from code.logging import logger
from code.utils import normalize_keywords
import asyncio
import os


@bot.callback_query_handler(func=call_factory.filter(area='conspects_upload').check)
async def callback_handler(call):
	logger.debug('Handle callback in creation...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'upload_conspect':
			await create_conspect(user_id=user_id, chat_id=chat_id)
			try:
				await bot.delete_message(chat_id=chat_id, message_id=message_id)
			except:
				logger.warning(f"Can't delete message {message_id}")


@bot.message_handler(commands=['new_conspect'])
async def create_conspect(message=None, user_id=None, chat_id=None):

	if user_id is None:
		user_id = message.from_user.id
	if chat_id is None:
		chat_id = message.chat.id

	conspect_date, theme, upload_date = '', '', ''

	try:
		# Предлагаем выбор предмета
		try:
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
					await send_temporary_message(chat_id, text = '<b>Не удалось найти предметы.</b>\n'
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


		except Exception as e:
			logger.error("Unexpected error occurred: %s", e)
			await stop_creation(chat_id, user_id)
			return
		files = []
		attempts, max_attempts = 0, 5
		while len(files)==0:
			attempts += 1
			files = await request_files(
				user_id=user_id,
				chat_id=chat_id,
				request_message='Отправьте файлы конспекта (фото или документ)'

			)
			if attempts > max_attempts:
				await stop_creation(chat_id, user_id)
				return
			if len(files) == 0:
				await send_temporary_message(chat_id, 'Вы не приложили ни одного файла.\nПовторите попытку')
				await asyncio.sleep(0.3)
				files = []
				continue

		file_paths = await save_files(files, save_dir='files/conspect_files')
		theme, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите тему текущего конспекта:',
			validator=validators.theme
		)
		if theme is None:
			logger.info("Theme request returned None — stopping creation conspect", extra={"user_id": user_id})
			await stop_creation(chat_id, user_id)
			return
		conspect_date, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите дату текущего конспекта в формате ДД.ММ.ГГГГ\nЕсли не знаете - напишите текущую дату):',
			validator=validators.conspect_date
		)
		if conspect_date is None:
			logger.info("Surname request returned None — stopping conspect", extra={"user_id": user_id})
			await stop_creation(chat_id, user_id)
			return

		keywords, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите ключевые слова для поиска через пробел или запятую.\n'
			                'Это очень поможет пользователям найти ваш конспект.'

		)
		keywords = await normalize_keywords(keywords)


		upload_date = datetime.now(ZoneInfo('Europe/Ulyanovsk')).strftime("%S:%M:%H %d.%m.%Y")
	except Exception as e:
		logger.exception("Unexpected error during creation flow", exc_info=e)
		await send_temporary_message(chat_id, 'Произошла ошибка при вводе данных. Попробуйте ещё раз.', delay_seconds=10)
		return

	# TODO В accept_creation также передаёшь ключевые слова и пути до сохранённых файлов
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


async def stop_creation(chat_id, user_id, file_paths=None):
	logger.info("stop_creation called — user cancelled the flow", extra={"chat_id": chat_id})
	await send_temporary_message(chat_id, 'Завершаю создание конспекта...', delay_seconds=10)
	try:
		await delete_files(file_paths)
	except:
		logger.error("Не удалось очистить файлы. Возможна утечка памяти.")
	await main_menu(user_id, chat_id)
	raise Exception('Interrupt creation')


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
		conspect_info = (f"<blockquote><b>Предмет: </b> {subject_name}\n"
		             f"<b>Тема: </b> {theme}\n"
		             f"<b>Дата конспекта: </b> {conspect_date}\n"
		             f"<b>Ключевые слова: </b> {keywords}</blockquote>\n")

		await send_message_with_files(
			chat_id=chat_id,
			files_text=conspect_info,
			file_paths=file_paths
		)
		accept_button = InlineKeyboardButton('Да', callback_data='True')
		decline_button = InlineKeyboardButton('Да', callback_data='False')
		cancel_button = InlineKeyboardButton('Да', callback_data='None')
		markup = InlineKeyboardMarkup([[accept_button, decline_button, cancel_button]])
		message = await bot.send_message(chat_id, text='Выложить этот конспект в открытый доступ?', reply_markup=markup)
		response = await wait_for_callback_on_message(
			user_id=user_id,
			chat_id=chat_id,
			message_id = message.id
		)
		if response == 'None':
			response = None
	except Exception as e:
		logger.exception("Error while asking for creation confirmation", exc_info=e)
		await send_temporary_message(chat_id, text='Произошла ошибка. Повторите позже.', delay_seconds=5)
		await stop_creation(chat_id, user_id, file_paths)
		return
	if response is None or response == False:
		logger.info("User cancelled at confirmation step", extra={"user_id": user_id})
		await send_temporary_message(chat_id, text='Отменяю создание конспекта...', delay_seconds=5)
		await stop_creation(chat_id, user_id, file_paths)
		return
	keywords_str = ", ".join(keywords.split(' '))
	if response:
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
	pass
