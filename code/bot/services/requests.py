# TODO Сделать request_accept, который просто будет выводить информацию и две кнопки, возвращать True или False

import asyncio
from typing import List

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.utils import send_temporary_message, delete_message_after_delay
from code.bot.states import MainStates

awaiters: dict[tuple[int, int], asyncio.Future] = {}


async def _save_waiting_for_flag(user_id, chat_id, waiting_for):
	async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
		data['waiting_for'] = waiting_for
async def _set_request_state(user_id, chat_id):
	await bot.set_state(user_id=user_id,chat_id=chat_id, state=MainStates.request_state)
async def _set_default_state(user_id, chat_id):
	await bot.set_state(user_id=user_id, chat_id=chat_id, state=MainStates.default_state)

# Запрашивает и ждёт у пользователя информацию
async def request(user_id, chat_id,
				  timeout: float = 60.0,
				  request_message: str = 'Введите:',
				  waiting_for: str = 'temp',
				  validator=None,
				  max_retries: int | None = 3,
				  previous_message_id: int | None = None,
				  delete_request_message: bool = True
				  ):
	"""
	Запрашивает у пользователя некоторую информацию, возвращает его ответ

	:param user_id: Айди юзера
	:param chat_id: Айди чата
	:param timeout: Время ожидания запроса
	:param request_message: Сообщение, которое бот выведет при запросе у пользователя
	:param waiting_for: Поле из data, куда будет записана информация (необязательно, но удобно)
	:param validator: Проверяет вводимые данные
	:param max_retries: Максимальное количество попыток
	:param previous_message_id: id прошлого сообщения
	:param delete_request_message: Если True - сообщения запроса и ответа пользователя будут удалены

	:return: str сообщения или None, если отменено или исчерпаны попытки
	"""
	# Проверяем, ожидаем ли мы от этого пользователя уже что-то
	waiting_for = 'message'
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')
	await _set_request_state(user_id, chat_id)
	loop = asyncio.get_running_loop()
	attempts = 0
	request_message_id = None
	# Получаем от пользователя ответ
	try:
		while True:
			attempts += 1
			# Создаём новый фьючер
			fut = loop.create_future()
			awaiters[key] = fut

			# Отправляем сообщение пользователю с запросом
			# Если это не первая попытка, то выводим сообщение временно (то есть оно удалится через несколько секунд)
			if request_message:
				if attempts > 1:
					await send_temporary_message(bot, chat_id, request_message, delay_seconds=5)
				else:
					request_message_id = (await bot.send_message(chat_id, request_message, parse_mode='HTML')).id

			# Добавляем флаг, куда будет сохраняться информация
			await _save_waiting_for_flag(user_id, chat_id, waiting_for)
			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				print(data)

			# Получаем от пользователя ответ из фьючера
			try:
				response = await asyncio.wait_for(fut, timeout)
			# Выводим сообщение, что время ввода истекло
			except asyncio.TimeoutError:
				await bot.send_message(chat_id, "Время ввода истекло")
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			finally:
				# Удаляем фьючер из ожидания
				awaiters.pop(key, None)

			# Если response = None - значит пользователь использовать команду /cancel => отменяем
			if response is None:
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None

			# Проверяем валидатором, если он есть, правильность в водимых данных
			err = None
			if validator is not None:
				if hasattr(validator, "validate"):
					ok, maybe_err = validator.validate(response.text.strip())
					if not ok:
						err = maybe_err or "Неверный ввод"
				else:
					maybe_err = validator(response)
					if maybe_err:
						err = maybe_err
			# Если валидатор вернул какую-то ошибку => выводим её
			if err:
				await delete_message_after_delay(bot, chat_id, response.id, delay_seconds=2)

				# Если закончились попытки - возвращаем None
				if max_retries is not None and attempts >= max_retries:
					await send_temporary_message(bot, chat_id, text=f"{err}\n<b>(исчерпаны попытки)</b>")
					async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
						data.pop('waiting_for', None)
					return None

				# В ином случае продолжаем цикл с новым сообщением
				request_message = f"{err}\nПопробуйте ещё раз или отмените командой /cancel."
				continue

			# В ином случае, сохраняем ответ в waiting_for и заметаем все следы
			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data[waiting_for] = response.text.strip()
				data.pop('waiting_for', None)
			if delete_request_message:
				await delete_message_after_delay(bot, chat_id, response.id, delay_seconds=2)
				await delete_message_after_delay(bot, chat_id, request_message_id, delay_seconds=2)
			return response.text.strip()
	finally:
		# Удаляем ожидание
		await _set_default_state(user_id, chat_id)
		awaiters.pop(key, None)


async def _generate_markup(start_index: int, end_index: int, confirmation_mode: bool = False) -> InlineKeyboardMarkup:
	"""
	:param start_index: Начальный индекс списка
	:param end_index: Конечный индекс списка
	:param confirmation_mode: Режим подтверждения (то есть, когда пользователь уже сделал выбор, и нужно его подтвердить)

	:return: InlineKeyboardMarkup - маркап сообщения
	"""
	markup = InlineKeyboardMarkup()

	# Если не confirmation_mode, то маркап - это просто список вариантов
	if not confirmation_mode:
		# Собираем массив кнопок
		list_buttons = []
		for i in range(start_index, end_index):
			button = InlineKeyboardButton(f'{i + 1}', callback_data=f'choice {i}')
			list_buttons.append(button)

		# Кнопки смены страницы и отмены
		previous_page_button = InlineKeyboardButton('<--', callback_data='previous page')
		cancel_button = InlineKeyboardButton('Отменить', callback_data='cancel')
		next_page_button = InlineKeyboardButton('-->', callback_data='next page')
		# Добавляем кнопки. Кнопки списка - отдельно от кнопок previous page, cancel и next page
		markup.add(*list_buttons, row_width=5)
		markup.row(previous_page_button, cancel_button, next_page_button)
	# Если установлен режим подтверждения, то создаём две кнопки - да или нет
	else:
		accept_button = InlineKeyboardButton('Правильно', callback_data='accept')
		repeat_button = InlineKeyboardButton('Выбрать другое', callback_data='repeat')
		markup.add(accept_button, repeat_button)
	return markup


# Проверка, есть ли ключ в объекте
async def _is_key_in_obj(row=None, key=None):
	try:
		_ = row[key]
		return True
	except Exception:
		return False


async def request_list(
		user_id: int,
		chat_id: int,
		timeout: float = 120.0,
		header: str = '',
		previous_message_id: int | None = None,
		items_list: list | tuple | dict = None,
		input_field: str = '',
		output_field: str | List[str] = '',
):
	"""
	Предлагает пользователю выбор из списка

	:param user_id: ID юзера.
	:param chat_id: ID чата.
	:param timeout: Время ожидания.
	:param header:  Сообщение в верхней строке.
	:param previous_message_id: ID прошлого сообщения (если есть, то сообщение будет меняться, а не выводиться новое).
	:param items_list: Список объектов.
	:param waiting_for: Поле из data, куда будет записана информация (необязательно, но удобно).
	:param input_field: Поле из объектов items_list, которое будет (!)показываться(!) пользователю.
	:param output_field: Поле из объектов items_list, которое будет возвращаться как результат работы функции.

	:return: Что угодно, в зависимости от items_list и output_field или None.
	"""
	waiting_for = 'callback'
	# Проверяем валидность списка
	if items_list is None:
		raise ValueError('items_list cannot be None')

	# Проверяем, не ожидаем ли мы уже от пользователя ответа
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')

	await _set_request_state(user_id, chat_id)
	loop = asyncio.get_running_loop()

	list_index = 0  # Текущий индекс первого элемента в списке
	MAX_ITEMS_ON_PAGE = 5  # Максимальное количество строчек в списке
	choice = None  # Индекс выбора пользователя
	confirmation_mode = False
	try:
		while True:
			# Создаём фьючер
			fut = loop.create_future()
			awaiters[key] = fut

			# Максимальный инедкс на странице - не должен превышать длины списка
			max_index = min(len(items_list), list_index + MAX_ITEMS_ON_PAGE)

			# Выводим сообщение с подтверждением выбора
			if confirmation_mode:
				if await _is_key_in_obj(row=items_list[choice], key=input_field):
					item = items_list[choice][input_field]
				else:
					item = items_list[choice]
				text = f'<b>Ваш выбор:</b> {item}\n\nЭто верно?'

			# Выводим список объектов
			else:
				text = f'{header}\n'
				for i in range(list_index, max_index):
					if await _is_key_in_obj(row=items_list[i], key=input_field):
						item = items_list[i][input_field]
					else:
						item = items_list[i]
					text += f'<b>{i + 1}. </b> {item}\n'
			# Генерируем markup в зависимости от режима
			markup = await _generate_markup(list_index, max_index, confirmation_mode)

			# Выводим сообщение. Если есть previous_message_id - меняем старое
			if previous_message_id:
				await bot.edit_message_text(
					chat_id=chat_id,
					message_id=previous_message_id,
					text=text,
					parse_mode='HTML')
				await bot.edit_message_reply_markup(
					chat_id=chat_id,
					message_id=previous_message_id,
					reply_markup=markup)
			# В ином случае выводим новое сообщение и сохраняем его ID
			else:
				previous_message_id = (await bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)).id

			# Сохраняем флаг waiting_for
			await _save_waiting_for_flag(user_id, chat_id, waiting_for)

			# Пробуем получить ответ от пользователя из фьючера
			try:
				response = await asyncio.wait_for(fut, timeout)
			except asyncio.TimeoutError:
				await bot.send_message(chat_id, "Время ввода истекло")
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			finally:
				# Удаляем ожидание
				awaiters.pop(key, None)

			# Если response = None - пользователь отменил запрос
			if response is None:
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None
			# Меняем страницы, если в response есть page
			if 'page' in response:
				p = response.split()  # Получаем первое слово
				match p[0]:
					case 'next':
						# Проверяем, есть ли следующая страница
						if list_index + MAX_ITEMS_ON_PAGE < len(items_list):
							list_index += MAX_ITEMS_ON_PAGE
					case 'previous':
						list_index -= MAX_ITEMS_ON_PAGE
				list_index = max(0, min(list_index, len(items_list)))
			# Если ответ - число => интерпретируем его как выбор
			elif 'choice' in response:
				choice = int(response.split()[1])
				confirmation_mode = True
			# Если в ответе 'repet', то обнуляем выбор и начинаем всё заново
			elif 'repeat' in response:
				choice = None
				confirmation_mode = False
				list_index = 0
				continue
			# Подтверждаем и возвращаем нужный выбор
			elif 'accept' in response and not choice is None:
				try:
					if isinstance(output_field, str):
						output_field = [output_field]
					output = []
					for field in output_field:
						if await _is_key_in_obj(row=items_list[choice], key=field):
							output.append(items_list[choice][field])
					if isinstance(output, list):
						if len(output) == 1:
							output = output[0]
						elif len(output) == 0:
							output = None
					return output
				except:
					return None
				finally:
					await delete_message_after_delay(
						bot,
						chat_id=chat_id,
						message_id=previous_message_id,
						delay_seconds=1)
			else:
				await send_temporary_message(
					bot,
					chat_id=chat_id,
					text='Не нажимайте никакие лишние кнопки',
					delay_seconds=1
				)
				continue
	finally:
		# Удаляем ожидание
		await _set_default_state(user_id, chat_id)
		awaiters.pop(key, None)


async def request_confirmation(
		user_id: int,
		chat_id: int,
		text: str = '\n',
		timeout: float = 60.0,
		accept_text: str = 'Подтвердить',
		decline_text: str = 'Отменить',
		previous_message_id: int = None,
		delete_message_after: bool = True
):
	"""
	Запрашивает у пользователя подтверждения чего-либо

	:param user_id: ID юзера.
	:param chat_id: ID чата.
	:param text: Текст, который будет выводиться как запрос.
	:param timeout: Время ожидания ответа.
	:param accept_text: Текст на кнопке подтверждения.
	:param decline_text: Текст на кнопке отклонения.
	:param waiting_for: Поле в data, куда сохраняется результат.
	:param previous_message_id: ID прошлого сообщения.
	:param delete_message_after: Время, после которого удаляется сообщение.

	:return: True или False, если сделан выбор; None - если отмена
	"""
	waiting_for = 'callback'
	key = (user_id, chat_id)
	# Проверяем, ожидаем ли мы от пользователя ответ
	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')

	await _set_request_state(user_id, chat_id)
	# Создаём фьючер и добавляем его в ожидание
	loop = asyncio.get_running_loop()
	fut = loop.create_future()
	awaiters[key] = fut

	# Собираем маркап
	accept_button = InlineKeyboardButton(text=accept_text, callback_data='accept')
	decline_button = InlineKeyboardButton(text=decline_text, callback_data='decline')
	markup = InlineKeyboardMarkup()
	markup.row(accept_button, decline_button)

	# Если есть previous_message_id, меняем его на новый
	if previous_message_id:
		await bot.edit_message_text(chat_id=chat_id, message_id=previous_message_id, text=text, parse_mode='HTML')
		await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)
	# В ином случае выводим сообщение и сохраняем его ID
	else:
		previous_message_id = (await bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')).id

	await _save_waiting_for_flag(user_id, chat_id, waiting_for)

	# Пробуем получить ответ
	try:
		response = await asyncio.wait_for(fut, timeout)
	except asyncio.TimeoutError:
		await bot.edit_message_text(text='Время ввода истекло.', chat_id=chat_id, message_id=previous_message_id)
		await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=None)
		if delete_message_after:
			await delete_message_after_delay(bot, chat_id=chat_id, message_id=previous_message_id, delay_seconds=1)
		async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
			data.pop('waiting_for', None)
		return False
	finally:
		# Удаляем из ожидания
		await _set_default_state(user_id, chat_id)
		awaiters.pop(key, None)

	# Если пользователь отменил
	if response is None:
		return None
	# Если пользователь отклонил
	if 'decline' in response:
		return False
	# Если пользователь подтвердил
	elif 'accept' in response:
		return True
	# Во всех остальных случаях возвращаем False
	return False

# TODO request_files
# TODO _handle_files
# Принимает все кнопки от пользователя, который находится в ожидании
@bot.callback_query_handler(func=lambda call: (call.from_user.id, call.message.chat.id) in awaiters)
async def _handle_awaited_callback(call):
	await bot.answer_callback_query(call.id)
	key = (call.from_user.id, call.message.chat.id)
	async with bot.retrieve_data(key[0], key[1]) as data:

		if data['waiting_for'] != 'callback':
			return
	fut = awaiters.get(key)
	if fut is None or fut.done():
		return
	response = call.data
	if 'cancel' in response:
		fut.set_result(None)
		await bot.send_message(call.message.chat.id, 'Ввод отменён')
	else:
		fut.set_result(response)


# Принимает все сообщения от пользователя, который находится в ожидании
@bot.message_handler(content_types=['text'], func=lambda m: (m.from_user.id, m.chat.id) in awaiters)
async def _handle_awaited_answer(message):
	key = (message.from_user.id, message.chat.id)
	async with bot.retrieve_data(key[0], key[1]) as data:
		if data['waiting_for'] != 'message':
			return
	fut = awaiters.get(key)
	if fut is None or fut.done():
		return
	text = message.text.strip()
	if 'cancel' in text:
		fut.set_result(None)
		await bot.send_message(message.chat.id, 'Ввод отменён')
	else:
		fut.set_result(message)
