from code.bot.handlers.main_menu import main_menu
from code.bot.services.files import delete_files
from code.bot.utils import send_message_with_files
from code.database.service import connect_db
from code.bot.bot_instance import bot
from code.database.queries import get, get_all, update, remove, remove_all
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
				print(conspect_row)
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
			        f'<b>👁️ Просмотры:</b> {int(conspect['views'])+1}</blockquote>\n')
			new_views = int(conspect['views']) + 1
			await update(
				database=db,
				table='CONSPECTS',
				values=[new_views, ],
				columns=['views', ],
				filters={'rowid': conspect['rowid']}
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
			subject = await get(
				database=db,
				table='SUBJECTS',
				filters={'rowid': conspect['subject_id']}
			)
			status = conspect['status']
			if status == 'accepted':
				status = '✅ Опубл.'
			elif status == 'pending':
				status = '⏳ Модерация'
			elif status == 'rejected':
				status = '❌ Отклонено'
			text = (f'{i}. <b>{conspect['theme']}</b>\n'
			        f'      {subject['name']}  •  {conspect['conspect_date']}\n'
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

async def get_conspects_list_slice(
		header: str,
		rule_line: str,
		conspects_formatted_list,
		first_index,
		last_index,
		current_page: int = None,
		last_page: int = None

):
	conspects_to_message = conspects_formatted_list[first_index:last_index]
	message_text = header + '\n<blockquote>'
	for conspect in conspects_to_message:
		message_text += conspect + '\n\n'
	message_text += '</blockquote>\n' + rule_line
	if not (current_page is None or last_page is None):
		message_text += f'\n<b><i>📖 Страница {current_page}/{last_page}</i></b>'

	return message_text

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