"""
Здесь обрабатываются все запросы к датабазе для юзеров
Получение информации, проверка, существует ли пользователь и т.д
"""

from code.database.queries import is_exists, get, insert
from code.database.service import connect_db
from code.logging import logger


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
		direction = await get(database=db, table='DIRECTIONS', filters={'rowid': user['direction_id']})
		chair = await get(database=db, table='CHAIRS', filters={'rowid': direction['chair_id']})
		facult = await get(database=db, table='FACULTS', filters={'rowid': chair['facult_id']})

	output = {
		'telegram_id': user['telegram_id'],
		'name': user['name'],
		'surname': user['surname'],
		'study_group': user['study_group'],
		'direction_id': direction['rowid'],
		'direction_name': direction['name'],
		'chair_id': chair['rowid'],
		'chair_name': chair['name'],
		'facult_id': facult['rowid'],
		'facult_name': facult['name']
	}
	return output
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

