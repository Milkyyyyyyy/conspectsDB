# TODO По хорошему здесь надо логику генерации форматированного текстового
# списка конспектов разделить на разные функции и вынести некоторые в services.conpsects.py


from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import wait_for_callback_on_message, request_confirmation
from code.bot.utils import safe_edit_message
from code.logging import logger
from code.bot.callbacks import call_factory
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from code.database.service import connect_db
from code.database.queries import get, get_all
from typing import List, Dict
import math
import asyncio
from code.bot.services.conspects import (make_list_of_conspects, generate_list_markup, get_conspects_list_slice,
                                         send_conspect_message, delete_conspect,
                                         get_all_subjects)


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


async def print_user_conspects(user_id, chat_id, conspects_list=None, conspects_per_page=10, page=1):
	markup = InlineKeyboardMarkup()


	conspects_amount = 0 if conspects_list is None else len(conspects_list)
	rule_line = '───────────────────────────\n'
	header = (f'📚 ВАШИ КОНСПЕКТЫ ({conspects_amount})\n'
	          '🔍 Фильтр: Все предметы\n\n') + rule_line
	if not conspects_list:
		back_button = InlineKeyboardButton('Назад в меню',
		                                   callback_data=call_factory.new(
			                                   area='main_menu',
			                                   action='main_menu'
		                                   )
		                                   )
		markup.row(back_button)
		text = header + '\n\n📭 У вас пока нет конспектов!'
		await bot.send_message(
			chat_id,
			text=text,
			reply_markup=markup
		)
		return

	last_page = math.ceil(conspects_amount / (conspects_per_page * page))

	back_button = InlineKeyboardButton('Назад в меню', callback_data='back')
	next_page_button = InlineKeyboardButton('--->', callback_data='next_page')
	previous_page_button = InlineKeyboardButton('<---', callback_data='previous_page')


	response = ''
	update_markup = True
	update_conspect_list = True
	previous_message_id=None
	conspects_formatted_list, conspect_by_index = await make_list_of_conspects(conspects_list)
	print(await get_all_subjects(conspects_list))
	while response != 'back':
		if update_conspect_list:
			conspects_formatted_list, conspect_by_index = await make_list_of_conspects(conspects_list)
			update_conspect_list = False

		first_index = (page-1)*conspects_per_page
		last_index = first_index + conspects_per_page
		if last_index > conspects_amount:
			last_index = conspects_amount

		message_text = await get_conspects_list_slice(
			header,
			rule_line,
			conspects_formatted_list,
			first_index,
			last_index,
			page,
			last_page
		)
		if update_markup:
			markup = await generate_list_markup(first_index, last_index)
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
			await print_conspect_by_index(
				user_id,
				chat_id,
				conspect_by_index,
				conspect_index,
				previous_message_id
			)
			update_markup = True
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
					# Удаляем markup со списка, чтобы пользователь не тыкал на неработающие кнопки
					try:
						await bot.edit_message_reply_markup(
							chat_id,
							previous_message_id,
							reply_markup=None
						)
					except Exception as e:
						logger.exception(f'Failed to edit message reply markup: {e}')

					asyncio.create_task(main_menu(user_id, chat_id))
					return



async def print_conspect_by_index(user_id, chat_id, conspects_by_index, conspect_index, previous_message_id = None):
	back_button = InlineKeyboardButton('Назад к конспектам', callback_data='back')
	delete_button = InlineKeyboardButton('Удалить конспект', callback_data='delete_conspect')
	markup=InlineKeyboardMarkup()
	markup.row(back_button)
	markup.row(delete_button)

	conspect = conspects_by_index[conspect_index]
	response = ''
	while response != 'back':
		message = await send_conspect_message(
			user_id,
			chat_id,
			conspect_row = conspect,
			reply_markup=markup,
			markup_text='Выберите действие'
		)
		response = await wait_for_callback_on_message(
			user_id,
			chat_id,
			message_id=message.id,
			timeout = 10
		)
		if response is None:
			response = 'back'
		match response:
			case 'back':
				try:
					await bot.delete_message(chat_id, message.id)
					await bot.delete_message(chat_id, message.id-1)
				except:
					logger.exception('Failed to delete message')
				return
			case 'delete_conspect':
				confirm = await request_confirmation(
					user_id,
					chat_id,
					'Вы уверены, что хотите удалить конспект?'
				)
				if confirm:
					await delete_conspect(
						conspect_row=conspect
					)
					message_id_to_delete = previous_message_id+1
					while True:
						await asyncio.sleep(0.25)
						try:
							await bot.delete_message(chat_id, message_id_to_delete)
						except:
							break
					return



async def user_conspect(user_id, chat_id):
	async with connect_db() as db:
		conspects = await get_all(
			database=db,
			table='CONSPECTS',
			filters={'user_telegram_id': user_id}
		)
	await print_user_conspects(user_id, chat_id, conspects_list=conspects)
