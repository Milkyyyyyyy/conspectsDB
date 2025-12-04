from code.bot.handlers.main_menu import main_menu
from code.bot.services.files import delete_files
from code.bot.utils import send_message_with_files
from code.database.service import connect_db
from code.bot.bot_instance import bot
from code.database.queries import get, get_all, update, remove, remove_all, is_exists, insert
from code.database.utils import safe_row_to_dict
from code.logging import logger
import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton



async def delete_conspect(conspect_id: int = None, conspect_row = None):
	if conspect_id is None and conspect_row is None:
		logger.error('Not provided conspect_id nor conspect_row')
		return None

	if conspect_id is None:
		conspect_id = conspect_row['rowid']
		conspect_row = None
	try:
		async with connect_db() as db:
			await remove(
				database=db,
				table='CONSPECTS',
				filters={'rowid': conspect_id}
			)
			paths_row = await get_all(
				database=db,
				table='CONSPECTS_FILES',
				filters={'conspect_id': conspect_id}
			)
			all_paths = []
			for path in paths_row:
				all_paths.append(path['path'])
			await delete_files(all_paths)
			await remove_all(
				database=db,
				table='CONSPECTS_FILES',
				filters={'conspect_id': conspect_id}
			)

	except Exception as e:
		logger.error(e)
		return False
	finally:
		return True

async def send_conspect_message(
		user_id,
		chat_id,
		conspect_id=None,
		reply_markup=None,
		markup_text=None,
		conspect_row=None,
):
	if conspect_id is None and conspect_row is None:
		logger.error('Not provided conspect_id nor conspect_row')
		return None
	file_paths =  []
	try:
		async with connect_db() as db:
			if conspect_row is None:
				conspect_row = await get(
					database=db,
					table = 'CONSPECTS',
					filters={
						'rowid': conspect_id
					}
				)
			else:
				conspect_id = conspect_row['rowid']
			if conspect_row is None:
				raise Exception(f'No conspect found with {conspect_id=}')
			conspect = dict(conspect_row)
			subject_row = await get(
				database=db,
				table = 'SUBJECTS',
				filters={
					'rowid': conspect['subject_id']
				}
			)
			subject_id = subject_row['rowid']
			if subject_row is None:
				raise Exception(f'No subject found with {subject_id=}')
			subject = dict(subject_row)
			subject_name = subject['name']

			paths_row = await get_all(
				database=db,
				table = 'CONSPECTS_FILES',
				filters={
					'conspect_id': conspect_id
				}
			)
			if not paths_row:
				raise Exception(f'No conspects files found for {conspect_id=}')

			for path in paths_row:
				file_paths.append(path['path'])

			keywords = conspect['keywords']
			text = (f'Информация о конспекте 📚\n'
			        f'<blockquote><b>🏫 Предмет:</b> {subject_name}\n'
			        f'<b>📝 Тема:</b> {conspect['theme']}\n'
			        f'<b>🏷️ Теги:</b> {keywords}\n'
			        f'<b>⭐ Рейтинг:</b> {conspect['rating']}\n'
			        f'<b>👁️ Просмотры:</b> {int(conspect['views'])}</blockquote>\n')
			await add_reaction(
				conspect_id=conspect_id,
				conspect_author_id=conspect['user_telegram_id'],
				user_id=user_id,
				reaction=0
			)
			message = await send_message_with_files(
				chat_id,
				file_paths=file_paths,
				files_text = text,
				markup_text=markup_text,
				reply_markup=reply_markup
			)
			return message

	except Exception as e:
		logger.exception(f'Error while fetching conspect from database: {e}')
		await bot.send_message(chat_id, 'Не удалось найти конспект')
		await asyncio.sleep(0.5)
		asyncio.create_task(main_menu(user_id, chat_id))
		return None

async def make_list_of_conspects(conspects_list):
	formatted_list=[]
	conspect_dict = {}
	async with connect_db() as db:
		for i, conspect in enumerate(conspects_list, start=1):
			if not isinstance(conspect, dict):
				conspect =await safe_row_to_dict(conspect)
			subject_name = conspect.get('subject_name', None)
			if not subject_name:
				subject = await get(
					database=db,
					table='SUBJECTS',
					filters={'rowid': conspect['subject_id']}
				)
				subject_name = subject['name']
			status = conspect['status']
			if status == 'accepted':
				status = '✅ Проверено'
			elif status == 'pending':
				status = '⏳ Модерация'
			elif status == 'rejected':
				status = '❌ Отклонено'
			text = (f'{i}. <b>{conspect['theme']}</b>\n'
			        f'      {subject_name}  •  {conspect['conspect_date']}\n'
			        f'      👁 {conspect['views']}  • ⭐️ {conspect['rating']}  •  {status}')
			formatted_list.append(text)
			conspect_dict[i-1] = conspect
	return formatted_list, conspect_dict

async def generate_list_markup(first_index, last_index, markup=None, numbers_per_line=5):
	if markup is None:
		markup = InlineKeyboardMarkup()

	next_row = []
	for i in range(first_index, last_index):
		button = InlineKeyboardButton(f'{i+1}', callback_data=f'conspect {i}')
		next_row.append(button)
		if len(next_row) >= numbers_per_line:
			markup.row(*next_row)
			next_row = []
	if len(next_row) != 0:
		markup.row(*next_row)
	return markup
async def get_conspect_files_amount(consepct_id=None, conspect_row=None):
	if consepct_id is None and conspect_row is None:
		return 0
	async with connect_db() as db:
		if conspect_row is None:
			conspect_row = await get(
				database=db,
				table='CONSPECTS',
				filters={'rowid':conspect_row}
			)
		else:
			conspect_id = conspect_row['rowid']

		files = await get_all(
			database=db,
			table='CONSPECTS_FILES',
			filters={'conspect_id': conspect_id}
		)
	return len(files)
async def get_conspects_list_slice(
		header: str,
		rule_line: str,
		conspects_formatted_list,
		first_index,
		last_index,
		current_page: int = None,
		last_page: int = None

):
	if len(conspects_formatted_list) == 0:
		message_text = header +'\n<blockquote>'
		message_text += 'Ничего не найдено\n' + '\n</blockquote>' + rule_line
		return message_text
	conspects_to_message = conspects_formatted_list[first_index:last_index]
	message_text = header + '\n<blockquote>'
	for conspect in conspects_to_message:
		message_text += conspect + '\n\n'
	message_text += '</blockquote>\n' + rule_line
	if not (current_page is None or last_page is None):
		message_text += f'\n<b><i>📖 Страница {current_page}/{last_page}</i></b>'

	return message_text

conspects_to_update = set()
async def get_reaction(conspect_id, user_id):
	async with connect_db() as db:
		reaction_row = await get(
			database=db,
			table='REACTIONS',
			filters={'user_telegram_id': user_id,
			         'conspect_id': conspect_id}
		)
	if not reaction_row:
		return None
	else:
		return reaction_row['reaction']
async def add_reaction(conspect_id, conspect_author_id, user_id, reaction):
	global conspects_to_update
	async with connect_db() as db:
		if str(user_id) != str(conspect_author_id):
			reaction_row = await get(
				database=db,
				table='REACTIONS',
				filters={'user_telegram_id': user_id,
				         'conspect_id': conspect_id}
			)
			is_already_exists = (reaction_row is not None)
			if not is_already_exists:
				conspects_to_update.add(conspect_id)
				await insert(
					database=db,
					table='REACTIONS',
					filters={
						'user_telegram_id': user_id,
						'conspect_id': conspect_id,
						'reaction': reaction
					}
				)
			elif reaction_row['reaction'] != reaction:
				conspects_to_update.add(conspect_id)
				await update(
					database=db,
					table='REACTIONS',
					filters={
						'user_telegram_id': user_id,
						'conspect_id': conspect_id,
					},
					values=[reaction, ],
					columns=['reaction', ]
				)




async def update_all_views_and_reactions(hard_update=False):
	global conspects_to_update
	conspects_ids = list(conspects_to_update.copy())
	conspects_to_update.clear()
	if len(conspects_ids) == 0 and not hard_update:
		return
	logger.info("Starting update_all_views_and_reactions")
	async with connect_db() as db:
		logger.debug("Database connection established")
		for conspect_id in conspects_ids:
			reactions = await get_all(
				database=db,
				table='REACTIONS',
				filters={'conspect_id': conspect_id}
			)
			views = len(reactions)
			rating = 0
			for reaction in reactions:
				rating += int(reaction['reaction'])

			await update(
				database=db,
				table='CONSPECTS',
				filters={'rowid': conspect_id},
				values=[views, rating],
				columns=['views', 'rating']
			)
			conspects_ids.remove(conspect_id)


		if hard_update:
			conspects = await get_all(
				database=db,
				table='CONSPECTS'
			)
			logger.info(f"Retrieved {len(conspects)} conspects from database")
			for idx, conspect in enumerate(conspects, 1):
				conspect_id = conspect['rowid']
				logger.debug(f"Processing conspect {idx}/{len(conspects)}, ID: {conspect_id}")

				reactions = await get_all(
					database=db,
					table='REACTIONS',
					filters={
						'conspect_id': conspect_id
					}
				)

				views = len(reactions)
				rating = 0
				for reaction in reactions:
					rating += int(reaction['reaction'])
				logger.debug(f"Conspect ID {conspect_id}: views={views}, rating={rating}")

				await update(
					database=db,
					table='CONSPECTS',
					filters={'rowid': conspect_id},
					values=[views, rating],
					columns=['views', 'rating']
				)

				logger.debug(f"Updated conspect ID {conspect_id} successfully")

			logger.info(f"Successfully updated {len(conspects)} conspects")
async def get_all_subjects(conspects_list):
	subject_ids = set()
	for conspect in conspects_list:
		subject_ids.add(conspect['subject_id'])
	subject_ids = list(subject_ids)

	subjects = []
	async with connect_db() as db:
		all_subjects = await get_all(
			database=db,
			table='SUBJECTS',
			filters = {'rowid': subject_ids}
		)
	for item in all_subjects:
		subjects.append(await safe_row_to_dict(item))
	return subjects