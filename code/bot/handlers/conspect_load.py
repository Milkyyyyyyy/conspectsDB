from datetime import datetime
from zoneinfo import ZoneInfo

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.services.files import save_files, delete_files
from code.bot.services.requests import request, request_list, request_confirmation, request_files
from code.bot.services.validation import validators
from code.bot.utils import send_temporary_message
from code.database.queries import get_all, get
from code.database.service import connect_db
from code.logging import logger
from code.utils import normalize_keywords
import os


@bot.callback_query_handler(func=call_factory.filter(area='conspects_menu').check)
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
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)


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
			with connect_db() as db:
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

				# Получаем все предметы из датабазы
				all_subjects = await get_all(
					database=db,
					table='SUBJECTS',
					filters=subject_filters,
					operator='OR'
				)
			subject_id = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				header='Выберите предмет',
				items_list=all_subjects,
				input_field='name',
				output_field='rowid'
			)



		except Exception as e:
			logger.error("Unexpected error occurred: %s", e)
			await stop_creation(chat_id)
			return

		theme = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите тему текущего конспекта:',
			validator=validators.theme
		)
		if theme is None:
			logger.info("Theme request returned None — stopping creation conspect", extra={"user_id": user_id})
			await stop_creation(chat_id)
			return
		conspect_date = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите дату текущего конспекта в формате ДД.ММ.ГГГГ (если не знаете - напишите текущую дату):',
			validator=validators.conspect_date
		)
		if conspect_date is None:
			logger.info("Surname request returned None — stopping conspect", extra={"user_id": user_id})
			await stop_creation(chat_id)
			return

		keywords = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите ключевые слова для поиска через пробел или иной разделитель (или оставьте пустым)'

		)
		keywords = normalize_keywords(keywords)

		files = await request_files(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Отправьте файлы конспекта (фото или документ)'

		)
		file_paths = await save_files(files)

		upload_date = datetime.now(ZoneInfo('Europe/Ulyanovsk')).strftime("%S:%M:%H %d.%m.%Y")
	except Exception as e:
		logger.exception("Unexpected error during creation flow", exc_info=e)
		await send_temporary_message(chat_id, 'Произошла ошибка при вводе данных. Попробуйте ещё раз.', delay_seconds=5)
		return

	# TODO В accept_creation также передаёшь ключевые слова и пути до сохранённых файлов
	await accept_creation(
		user_id=user_id,
		chat_id=chat_id,
		subject_id=subject_id,
		theme=theme,
		keywords=keywords,
		conspect_date=conspect_date,
		upload_date=upload_date,
		file_paths=file_paths
	)


async def stop_creation(chat_id, file_paths=None):
	logger.info("stop_creation called — user cancelled the flow", extra={"chat_id": chat_id})
	await send_temporary_message(chat_id, 'Завершаю создание конспекта...', delay_seconds=10)
	try:
		await delete_files(file_paths)
	except:
		logger.error("Не удалось очистить файлы. Возможна утечка памяти.")
	raise Exception('Interrupt creation')


async def accept_creation(
		user_id=None,
		chat_id=None,
		subject_id=None,
		keywords=None,
		theme=None,
		conspect_date=None,
		upload_date=None,
		file_paths=None

):
	logger.debug("Presenting registration confirmation to user",
	             extra={"user_id": user_id, "chat_id": chat_id,
	                    "theme": theme, "conspect_date": conspect_date, "upload_date": upload_date})
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
	buttons.add(InlineKeyboardButton("Повторить попытку", callback_data="register"))
	text = (f"Проверьте правильность данных\n\n"
	        f"<blockquote><b>Тема</b>: {theme}\n"
	        f"<b>Дата конспекта</b>: {conspect_date}\n"
	        f"<b>Дата загрузки конспекта</b>: {upload_date}\n")
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
		response = await request_confirmation(
			user_id=user_id,
			chat_id=chat_id,
			text=text,
			accept_text='Всё правильно',
			decline_text='Повторить попытку',
		)
	except Exception as e:
		logger.exception("Error while asking for creation confirmation", exc_info=e)
		await send_temporary_message(chat_id, text='Произошла ошибка. Повторите позже.', delay_seconds=5)
		return
	if response is None:
		logger.info("User cancelled at confirmation step", extra={"user_id": user_id})
		await send_temporary_message(chat_id, text='Отменяю создание конспекта...', delay_seconds=5)
		# TODO Если пользователь отменить создание конспекта -- сначала удали все сохранённые файлы
		return
	if response:
		logger.info("User accepted registration — proceeding to save", extra={"user_id": user_id})
		await end_creation(
			user_id=user_id,
			chat_id=chat_id,
			subject_id=subject_id,
			keywords=keywords,
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
