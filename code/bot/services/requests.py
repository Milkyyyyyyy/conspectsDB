from code.bot.bot_instance import bot
from code.bot.utils import send_temporary_message, delete_message_after_delay
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from typing import Pattern, Optional, Tuple, Dict
awaiters: dict[tuple[int, int], asyncio.Future] = {}

async def request(user_id, chat_id,
                  timeout: float = 60.0,
                  request_message: str = 'Введите:',
                  waiting_for: str = 'temp',
                  validator = None,
                  max_retries: int | None = 3,
				  previous_message_id: int | None = None,):
	"""
	:param user_id: Айди юзера
	:param chat_id: Айди чата
	:param timeout: Время ожидания запроса
	:param request_message: Сообщение, которое бот выведет при запросе у пользователя
	:param waiting_for: Поле из data, куда будет записана информация (необязательно, но удобно)
	:param validator: Проверяет вводимые данные
	:param max_retries: Максимальное количество попыток
	:param previous_message_id: id прошлого сообщения

	:return: str сообщения или None, если отменено или исчерпаны попытки
	"""
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')

	loop = asyncio.get_running_loop()
	attempts = 0
	try:
		while True:
			attempts += 1
			fut = loop.create_future()
			awaiters[key] = fut
			if request_message:
				if attempts > 1:
					await send_temporary_message(bot, chat_id, request_message, delay_seconds=5)
				else:
					await bot.send_message(chat_id, request_message, parse_mode='HTML')

			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data['waiting_for'] = waiting_for

			try:
				message = await asyncio.wait_for(fut, timeout)
			except asyncio.TimeoutError:
				await bot.send_message(chat_id, "Время ввода истекло")
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			finally:
				awaiters.pop(key, None)

			if message is None:
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None

			err = None
			if validator is not None:
				if hasattr(validator, "validate"):
					ok, maybe_err = validator.validate(message.text.strip())
					if not ok:
						err = maybe_err or "Неверный ввод"
				else:
					maybe_err = validator(message)
					if maybe_err:
						err = maybe_err
			if err:
				await delete_message_after_delay(bot, chat_id, message.id, delay_seconds=2)
				if max_retries is not None and attempts >= max_retries:
					await send_temporary_message(bot, chat_id, text=f"{err}\n<b>(исчерпаны попытки)</b>")
					async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
						data.pop('waiting_for', None)
					return None
				request_message = f"{err}\nПопробуйте ещё раз или отмените командой /cancel."
				continue
			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data[waiting_for] = message
				data.pop('waiting_for', None)
			return message.text.strip()
	finally:
		awaiters.pop(key, None)
async def _generate_markup(start_index: int, end_index: int, confirmation_mode: bool = False):
	markup = InlineKeyboardMarkup()
	if not confirmation_mode:
		row = []
		print(start_index, end_index)
		for i in range(start_index, end_index):
			button = InlineKeyboardButton(f'{i+1}', callback_data=f'{i}')
			row.append(button)
		previous_page_button = InlineKeyboardButton('<--', callback_data='previous page')
		cancel_button = InlineKeyboardButton('Отменить', callback_data='cancel')
		next_page_button = InlineKeyboardButton('-->', callback_data='next page')
		markup.add(*row, row_width=5)
		markup.row(previous_page_button, cancel_button, next_page_button)
	else:
		accept_button = InlineKeyboardButton('Правильно', callback_data='accept')
		repeat_button = InlineKeyboardButton('Выбрать другое', callback_data='repeat')
		markup.add(accept_button, repeat_button)
	return markup


async def request_list(
		user_id: int,
		chat_id: int,
		timeout: float=60.0,
		header: str = '',
		previous_message_id: int | None = None,
		items_list: list | tuple = None,
		waiting_for: str = '',
):
	if items_list is None:
		raise ValueError('items_list cannot be None')
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')

	loop = asyncio.get_running_loop()
	list_index = 0
	MAX_ITEMS_ON_PAGE = 5
	choice = None
	confirmation_mode = False
	try:
		while True:
			fut = loop.create_future()
			awaiters[key] = fut

			max_index = min(len(items_list), list_index + MAX_ITEMS_ON_PAGE)
			
			if confirmation_mode:
				text=f'<b>Ваш выбор:</b> {choice}\n\nЭто верно?'
			else:
				text = f'{header}\n'
				for i in range(list_index, max_index):
					text += f'<b>{i+1}. </b> {items_list[i]}\n'
			markup = await _generate_markup(list_index, max_index, confirmation_mode)
			if previous_message_id:
				await bot.edit_message_text(chat_id=chat_id, message_id=previous_message_id, text=text, parse_mode='HTML')
				await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)
			else:
				previous_message_id = (await bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)).id

			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data['waiting_for'] = waiting_for

			try:
				response = await asyncio.wait_for(fut, timeout)
			except asyncio.TimeoutError:
				await bot.send_message(chat_id, "Время ввода истекло")
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			finally:
				awaiters.pop(key, None)

			if response is None:
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			print(response)
			if 'page' in response:
				p = response.split()
				match p[0]:
					case 'next':
						list_index += MAX_ITEMS_ON_PAGE
					case 'previous':
						list_index -= MAX_ITEMS_ON_PAGE
				list_index = max(0, min(list_index, len(items_list)))
			elif response.isnumeric():
				choice = items_list[int(response)]
				confirmation_mode = True
			elif 'repeat' in response:
				choice = None
				confirmation_mode = False
				list_index = 0
				continue
			elif 'accept' in response and choice:
				try:
					return choice
				except:
					return None
				finally:
					await delete_message_after_delay(bot, chat_id=chat_id, message_id=previous_message_id, delay_seconds=1)
	finally:
		awaiters.pop(key, None)


@bot.callback_query_handler(func=lambda call: (call.from_user.id, call.message.chat.id) in awaiters)
async def _handle_awaited_callback(call):
	await bot.answer_callback_query(call.id)
	key = (call.from_user.id, call.message.chat.id)
	fut = awaiters.get(key)
	if fut is None or fut.done():
		return
	response = call.data
	if 'cancel' in response:
		fut.set_result(None)
		await bot.send_message(call.message.chat.id, 'Ввод отменён')
	else:
		fut.set_result(response)
@bot.message_handler(func=lambda m: (m.from_user.id, m.chat.id) in awaiters)
async def _handle_awaited_answer(message):
	key = (message.from_user.id, message.chat.id)
	fut = awaiters.get(key)
	if fut is None or fut.done():
		return
	text = message.text.strip()
	if 'cancel' in text:
		fut.set_result(None)
		await bot.send_message(message.chat.id, 'Ввод отменён')
	else:
		fut.set_result(message)


