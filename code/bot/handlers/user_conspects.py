# TODO По хорошему здесь надо логику генерации форматированного текстового
# списка конспектов разделить на разные функции и вынести некоторые в services.conpsects.py

import asyncio

from aiohttp.web_routedef import delete

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import wait_for_callback_on_message
from code.bot.utils import safe_edit_message
from code.logging import logger
from code.bot.callbacks import call_factory
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from code.database.service import connect_db
from code.database.queries import get, get_all
from typing import List, Dict
import math
import asyncio

@bot.callback_query_handler(func=call_factory.filter(area='user_conspects').check)
async def callback_handler(call):
	logger.debug('Handle callback in user_conspects...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id
	username = call.from_user.username

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'user_conspects':
			await user_conspect(user_id, chat_id)
async def _make_list_of_conspects(conspects_list):
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
async def _generate_list_markup(first_index, last_index, markup=None, numbers_per_line=5):
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
async def print_user_conspects(user_id, chat_id, conspects_list=None, conspects_per_page=10, page=1):
	markup = InlineKeyboardMarkup()


	conspects_amount = 0 if conspects_list is None else len(conspects_list)
	rule_line = '───────────────────────────\n'
	header = (f'📚 ВАШИ КОНСПЕКТЫ ({conspects_amount})\n'
	          '🔍 Фильтр: Все предметы\n\n') + rule_line
	if not conspects_list:
		back_button = InlineKeyboardButton('Назад в меню',
		                                   callback_data=call_factory.new(
			                                   area='user_conspects',
			                                   action='user_conspects'
		                                   )
		                                   )
		markup.row(back_button)
		text = header + '\n\n📭 У вас пока нет конспектов!'
		await bot.send_message(
			chat_id,
			text=text,
			replymarkup=markup
		)
		return

	last_page = math.ceil(conspects_amount / (conspects_per_page * page))

	back_button = InlineKeyboardButton('Назад в меню', callback_data='back')
	next_page_button = InlineKeyboardButton('--->', callback_data='next_page')
	previous_page_button = InlineKeyboardButton('<---', callback_data='previous_page')


	response = ''
	conspects_formatted_list, conspect_by_index = await _make_list_of_conspects(conspects_list)
	update_markup = True
	previous_message_id=None
	while response != 'back':
		first_index = (page-1)*conspects_per_page
		last_index = first_index + conspects_per_page
		if last_index > conspects_amount:
			last_index = conspects_amount

		conspects_to_message = conspects_formatted_list[first_index:last_index]
		message_text = header + '\n<blockquote>'
		for conspect in conspects_to_message:
			message_text += conspect + '\n\n'
		message_text += '</blockquote>\n' + rule_line

		if update_markup:
			markup = await _generate_list_markup(first_index, last_index)
			markup.row(previous_page_button, next_page_button)
			markup.row(back_button)
			previous_message_id = await safe_edit_message(
				previous_message_id=previous_message_id,
				chat_id=chat_id,
				user_id=user_id,
				text=message_text,
				reply_markup=markup
			)
			update_markup = False
		response = await wait_for_callback_on_message(
			user_id,
			chat_id,
			message_id=previous_message_id,
			timeout = 60*2,
			delete_callback_after=False
		)
		if response is None:
			response = 'back'
		if 'conspect' in response:
			conspect_index = int(response.split()[-1])
			print(conspect_index)
			await print_conspect_by_index(chat_id, conspect_by_index, conspect_index)
		else:
			match response:
				case 'next_page':
					if page != last_page:
						page+=1
						update_markup = True
				case 'previous_page':
					if page != 1:
						page-=1
						update_markup = True
				case 'back':
					asyncio.create_task(main_menu(user_id, chat_id))
					return



async def print_conspect_by_index(chat_id, conspects_by_index, conspect_index):
	conspect = conspects_by_index[conspect_index]
	# TODO доделать
async def user_conspect(user_id, chat_id):
	async with connect_db() as db:
		conspects = await get_all(
			database=db,
			table='CONSPECTS',
			filters={'user_telegram_id': user_id}
		)
	await print_user_conspects(user_id, chat_id, conspects_list=conspects)
