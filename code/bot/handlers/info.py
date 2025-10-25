from code.database.queries import connectDB, get

async def get_user_info(chat_id=None, user_id=None):
	if chat_id is None or user_id is None:
		return None
	async with connectDB() as db:
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