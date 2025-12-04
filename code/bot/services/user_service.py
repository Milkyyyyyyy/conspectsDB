"""
Здесь обрабатываются все запросы к датабазе для юзеров
Получение информации, проверка, существует ли пользователь и т.д
"""
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.utils import send_temporary_message

from code.database.queries import is_exists, get, insert, get_all, update
from code.database.service import connect_db
from code.logging import logger
from code.database.utils import safe_row_to_dict


# Возвращает True, если пользователь зарегистрирован
async def is_user_exists(user_id):
	async with connect_db() as database:
		logger.debug(database)
		user_id = str(user_id)
		isUserExists = await is_exists(database=database, table="USERS", filters={"telegram_id": user_id})
	return isUserExists


async def get_user_info(chat_id=None, user_id=None):
	if chat_id is None or user_id is None:
		return None
	async with connect_db() as db:
		user = await get(database=db, table='USERS', filters={'telegram_id': user_id})
		direction_id = user['direction_id']
		direction = await get(database=db, table='DIRECTIONS', filters={'rowid': direction_id})
		direction = await safe_row_to_dict(direction)
		chair_id = direction.get('chair_id', None)
		if chair_id is None:
			chair = {}
			facult = {}
		else:
			chair = await get(database=db, table='CHAIRS', filters={'rowid': chair_id})
			chair = await safe_row_to_dict(chair)
			facult_id = chair.get('facult_id', None)
			if chair_id is None:
				facult = {}
			else:
				facult = await get(database=db, table='FACULTS', filters={'rowid': facult_id})
				facult = await safe_row_to_dict(facult)

		conspect_rows = await get_all(
			database=db,
			table='CONSPECTS',
			filters = {'user_telegram_id': user_id}
		)


	output = {
		'telegram_id': user['telegram_id'],
		'name': user['name'],
		'surname': user['surname'],
		'study_group': user['study_group'],
		'direction_id': direction_id,
		'direction_name': direction.get('name', 'Неизвестное направление'),
		'chair_id': chair.get('rowid', None),
		'chair_name': chair.get('name', 'Неизвестная кафедра'),
		'facult_id': facult.get('rowid', None),
		'facult_name': facult.get('name', 'Неизвестный факультет'),
		'all_conspects': conspect_rows
	}
	return output

async def change_user_info(chat_id, user_id, username, previous_message_id, values, columns):
	logger.info("Initiating change_name for user=%s chat=%s", user_id, chat_id)
	updated = None
	try:
		async with connect_db() as db:
			updated = await update(
				database=db,
				values=values,
				table='USERS',
				columns=columns,
				filters={'telegram_id': user_id}
			)
			logger.info("Database update result for user=%s: %r", user_id, updated)
	except Exception as e:
		logger.exception(f'Database update failed for user=%s\n{e}', user_id)
		await send_temporary_message(chat_id, text='Произошла ошибка!', delay_seconds=5)

		return
	finally:
		text = 'Обновлено' if updated else 'Не удалось обновить'
		await send_temporary_message(chat_id, text=text, delay_seconds=3)


async def save_user_in_database(user_id=None, name=None, surname=None, group=None, direction_id=None, role=None):
	logger.info('Saving user in database...')
	if None in (user_id, name, surname, group, direction_id, role):
		logger.error("Invalid arguments")
		return False
	if await is_user_exists(user_id):
		logger.error(f"User ({user_id}) already exists")
		return False
	logger.debug(f'User info:\n'
				 f'user_id={user_id}\n'
				 f'name={name}\n'
				 f'surname={surname}\n'
				 f'group={group}\n'
				 f'direction_id={direction_id}\n'
				 f'role={role}')
	async with connect_db() as db:
		filters = {
			'telegram_id': str(user_id),
			'name': name,
			'surname': surname,
			'study_group': group,
			'direction_id': direction_id,
			'role': 'user'
		}
		await insert(database=db, table='USERS', filters=filters)
	# Проверяем, сохранился ли пользователь
	return await is_user_exists(user_id)


async def ensure_user_registered(user_id, chat_id):
	exists = await is_user_exists(user_id)
	print(exists)
	if not exists:
		logger.info(f'The user ({user_id}) does not exist')
		text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду /register или нажмите на кнопку ниже'
		markup = InlineKeyboardMarkup()
		markup.add(InlineKeyboardButton(
			"Зарегистрироваться",
			callback_data=call_factory.new(
				area='registration',
				action="start_register"
			)
		)
		)
		await bot.send_message(chat_id, text, reply_markup=markup)
	return exists
