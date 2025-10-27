"""
В этом файле происходит обработка главного меню (пока что это только само главное меню и вывод информации о пользователе)
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import vote_cb
from code.bot.services.user_service import get_user_info
from code.bot.utils import get_greeting
from code.logging import logger


async def main_menu(user_id, chat_id, previous_message_id=None):
	logger.info(f'Printing main menu for user({user_id})')
	greeting = await get_greeting()
	# Собираем markup
	markup = InlineKeyboardMarkup()
	show_info = InlineKeyboardButton('О пользователе 👤', callback_data='show_info')
	markup.row(show_info)
	async with bot.retrieve_data(user_id, chat_id) as data:
		if previous_message_id is None:
			message = await bot.send_message(chat_id=chat_id, text=greeting, reply_markup=markup, parse_mode='HTML')
		else:
			await bot.edit_message_text(text=greeting, chat_id=chat_id, message_id=previous_message_id,
										parse_mode='HTML')
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'show_info')
async def print_user_info(call):
	logger.info(f"Showing user ({call.from_user.id}) user info")
	await bot.answer_callback_query(call.id)
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	user_info = await get_user_info(chat_id=chat_id, user_id=user_id)
	logger.debug(f'user_info = {user_info}')
	text_message = ("<blockquote><b>Информация о пользователе</b>\n\n"
					f"<b>Имя</b>: {user_info['name']}\n"
					f"<b>Фамилия</b>: {user_info['surname']}\n"
					f"<b>Юзернейм</b>: @{call.from_user.username}\n\n"
					f"<b>Учебная группа</b>: {user_info['study_group']}\n"
					f"<b>Факультет</b>: {user_info['facult_name']}\n"
					f"<b>Кафедра</b>: {user_info['chair_name']}\n"
					f"<b>Направление</b>: {user_info['direction_name']}\n\n"
					f"<b>Кол-во загруженных конспектов</b>: В РАЗРАБОТКЕ</blockquote>")
	markup = InlineKeyboardMarkup()
	back_button = InlineKeyboardButton('Назад', callback_data=vote_cb.new(action='open menu',
																		  amount=str(call.message.message_id)))
	change_
	markup.row(back_button)

	await bot.edit_message_text(text=text_message,
								chat_id=chat_id,
								message_id=call.message.message_id,
								parse_mode='HTML')
	await bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)

