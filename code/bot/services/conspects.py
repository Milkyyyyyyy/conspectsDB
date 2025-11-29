from code.bot.handlers.main_menu import main_menu
from code.bot.utils import send_message_with_files
from code.database.service import connect_db
from code.bot.bot_instance import bot
from code.database.queries import get, get_all
from code.logging import logger
import asyncio

async def send_conspect_message(user_id, chat_id, conspect_id, reply_markup=None, markup_text=None):
	file_paths =  []
	try:
		async with connect_db() as db:
			conspect_row = await get(
				database=db,
				table = 'CONSPECTS',
				filters={
					'rowid': conspect_id
				}
			)
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
			print(subject_row)
			if not paths_row:
				raise Exception(f'No conspects files found for {conspect_id=}')

			for path in paths_row:
				file_paths.append(path['path'])

			text = (f'Информация о конспекте 📚\n'
			        f'<blockquote><b>🏫 Предмет:</b> {subject_name}\n'
			        f'<b>📝 Тема:</b> {conspect['theme']}\n'
			        f'<b>⭐ Рейтинг:</b> {conspect['rating']}\n'
			        f'<b>👁️ Просмотры:</b> {conspect['views']}</blockquote>\n')
			await send_message_with_files(
				chat_id,
				file_paths=file_paths,
				files_text = text,
				markup_text=markup_text,
				reply_markup=reply_markup
			)

	except Exception as e:
		logger.exception(f'Error while fetching conspect from database: {e}')
		await bot.send_message(chat_id, 'Не удалось найти конспект')
		await asyncio.sleep(0.5)
		asyncio.create_task(main_menu(user_id, chat_id))
		return None