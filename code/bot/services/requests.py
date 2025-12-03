import asyncio
from typing import List

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.states import MainStates, set_default_state
from code.bot.utils import send_temporary_message, delete_message_after_delay, safe_edit_message
from code.logging import logger

awaiters: dict[tuple[int, int], asyncio.Future | asyncio.Queue] = {}
specific_awaiters: dict[tuple[int, int, int], asyncio.Future | asyncio.Queue] = {}

async def print_awaiters():
	print(awaiters)
	print(specific_awaiters)
async def  remove_awaiters(user_id, chat_id):
	key = (user_id, chat_id)
	logger.info(f'Removing awaiters with {key=}')
	if key in awaiters:
		del awaiters[key]

	keys_to_remove = [
		k for k in specific_awaiters
		if k[0] == user_id and k[1] == chat_id
	]

	for key in keys_to_remove:
		del specific_awaiters[key]



async def _save_waiting_for_flag(user_id, chat_id, waiting_for):
	async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
		data['waiting_for'] = waiting_for
		logger.debug('Set waiting_for for %s:%s -> %s', user_id, chat_id, waiting_for)


async def _set_request_state(user_id, chat_id):
	logger.debug('Setting request state for user=%s chat=%s', user_id, chat_id)
	await bot.set_state(user_id=user_id, chat_id=chat_id, state=MainStates.request_state)


# Запрашивает и ждёт у пользователя информацию
async def request(
		user_id, chat_id,
		timeout: float = 60.0,
		request_message: str = 'Введите:',
		validator=None,
		max_retries: int | None = 3,
		delete_request_message: bool = True,
		previous_message_id=None
		):
	"""
	Запрашивает у пользователя некоторую информацию, возвращает его ответ

	:param user_id: Айди юзера
	:param chat_id: Айди чата
	:param timeout: Время ожидания запроса
	:param request_message: Сообщение, которое бот выведет при запросе у пользователя
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
		logger.warning('Attempt to start request but already waiting for %s', key)
		raise RuntimeError('Already waiting for a response from the user')
	await _set_request_state(user_id, chat_id)
	loop = asyncio.get_running_loop()
	attempts = 0
	request_message_id = previous_message_id
	logger.debug('Send request to user (%s)', user_id)
	try:
		while True:
			attempts += 1
			fut = loop.create_future()
			awaiters[key] = fut
			# Отправляем сообщение пользователю с запросом
			try:
				if request_message:
					if attempts > 1:
						await send_temporary_message(chat_id, request_message, delay_seconds=5)
					else:
						# sent = await bot.send_message(chat_id, request_message, parse_mode='HTML')
						sent = await safe_edit_message(previous_message_id=previous_message_id,
						                               chat_id=chat_id,
						                               text=request_message)
						request_message_id = sent
						logger.debug('Sent request message id=%s to chat=%s', request_message_id, chat_id)

				# Добавляем флаг, что мы ожидаем
				await _save_waiting_for_flag(user_id, chat_id, waiting_for)

				# Получаем от пользователя ответ из фьючера
				try:
					response = await asyncio.wait_for(fut, timeout)
				# Выводим сообщение, что время ввода истекло
				except asyncio.TimeoutError:
					logger.info('Timeout waiting for user response %s', key)
					await bot.send_message(chat_id, "Время ввода истекло")
					async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
						data.pop('waiting_for', None)
					return None, previous_message_id
				finally:
					awaiters.pop(key, None)

				if response is None:
					logger.info('User cancelled input %s', key)
					async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
						data.pop('waiting_for', None)
					return None, previous_message_id

				user_response = response
				# Валидатор
				err = None
				if validator is not None:
					try:
						if hasattr(validator, "validate"):
							ok, maybe_err = validator.validate(response.text.strip())
							if not ok:
								err = maybe_err or "Неверный ввод"
						else:
							maybe_err = validator(response)
							if maybe_err:
								err = maybe_err
					except Exception as e:
						logger.exception('Validator raised exception for user (%s) message (%s): %s', key,
						                 response.text, e)
						err = 'Ошибка проверки'

				if err:
					logger.debug('Validation failed for %s: %s', key, err)
					await delete_message_after_delay(chat_id, response.id, delay_seconds=2)

					# Если закончились попытки - возвращаем None
					if max_retries is not None and attempts >= max_retries:
						await send_temporary_message(chat_id, text=f"{err}\n<b>(исчерпаны попытки)</b>")
						async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
							data.pop('waiting_for', None)
						return None, previous_message_id

					# В ином случае продолжаем цикл с новым сообщением
					request_message = f"{err}\nПопробуйте ещё раз или отмените командой /cancel."
					continue

				# Сохраняем ответ
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data[waiting_for] = response.text.strip()
					data.pop('waiting_for', None)
					logger.info('Saved response for %s: %s', key, response.text.strip())

				return response.text.strip(), request_message_id
			except Exception as e:
				logger.exception('Unexpected error in request loop for %s: %s', key, e)
	finally:
		await set_default_state(user_id, chat_id)
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
	:param input_field: Поле из объектов items_list, которое будет (!)показываться(!) пользователю.
	:param output_field: Поле из объектов items_list, которое будет возвращаться как результат работы функции.

	:return: Что угодно, в зависимости от items_list и output_field или None.
	"""
	waiting_for = 'callback'
	# Проверяем валидность списка
	if items_list is None:
		logger.error("request_list called without items_list for %s:%s", user_id, chat_id)
		raise ValueError('items_list cannot be None')

	# Проверяем, не ожидаем ли мы уже от пользователя ответа
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		logger.warning('Attempt to start request but already waiting for %s', key)
		raise RuntimeError('Already waiting for a response from the user')

	await _set_request_state(user_id, chat_id)
	loop = asyncio.get_running_loop()

	list_index = 0  # Текущий индекс первого элемента в списке
	MAX_ITEMS_ON_PAGE = 5  # Максимальное количество строчек в списке
	choice = None  # Индекс выбора пользователя
	confirmation_mode = False
	try:
		while True:
			fut = loop.create_future()
			awaiters[key] = fut

			max_index = min(len(items_list), list_index + MAX_ITEMS_ON_PAGE)

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
			# Генерируем reply_markup в зависимости от режима
			markup = await _generate_markup(list_index, max_index, confirmation_mode)

			# Выводим сообщение. Если есть previous_message_id - меняем старое
			previous_message_id = await safe_edit_message(
				previous_message_id=previous_message_id,
				chat_id=chat_id,
				user_id=user_id,
				text=text,
				reply_markup=markup
			)

			# Сохраняем флаг waiting_for
			await _save_waiting_for_flag(user_id, chat_id, waiting_for)

			# Пробуем получить ответ от пользователя из фьючера
			try:
				response = await asyncio.wait_for(fut, timeout)
			except asyncio.TimeoutError:
				logger.info("Timeout in request_list for %s", key)
				await send_temporary_message(chat_id, 'Время ввода истекло', delay_seconds=10)
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
				logger.info("User cancelled request_list %s", key)
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
					logger.info("request_list returning output for %s: %s", key, output)
					return output
				except Exception as e:
					logger.exception("Error while preparing output in request_list for %s: %s", key, e)
					return None
			else:
				await send_temporary_message(
					chat_id=chat_id,
					text='Не нажимайте никакие лишние кнопки',
					delay_seconds=1
				)
				continue
	finally:
		await delete_message_after_delay(
			chat_id=chat_id,
			message_id=previous_message_id,
			delay_seconds=1)
		await set_default_state(user_id, chat_id)
		awaiters.pop(key, None)


async def request_confirmation(
		user_id: int,
		chat_id: int,
		text: str = '\n',
		timeout: float = 60.0,
		accept_text: str = 'Подтвердить',
		decline_text: str = 'Отменить',
		previous_message_id: int = None,
		delete_message_after: bool = True,
		delete_markup_after_choice: bool = True
):
	"""
	Запрашивает у пользователя подтверждения чего-либо

	:param user_id: ID юзера.
	:param chat_id: ID чата.
	:param text: Текст, который будет выводиться как запрос.
	:param timeout: Время ожидания ответа.
	:param accept_text: Текст на кнопке подтверждения.
	:param decline_text: Текст на кнопке отклонения.
	:param previous_message_id: ID прошлого сообщения.
	:param delete_message_after: Время, после которого удаляется сообщение.

	:return: True или False, если сделан выбор; None - если отмена
	"""
	waiting_for = 'callback'
	key = (user_id, chat_id)
	if key in awaiters and not awaiters[key].done():
		logger.warning('Attempt to start request but already waiting for %s', key)
		raise RuntimeError('Already waiting for a response from the user')

	await _set_request_state(user_id, chat_id)

	loop = asyncio.get_running_loop()
	fut = loop.create_future()
	awaiters[key] = fut
	try:
		accept_button = InlineKeyboardButton(text=accept_text, callback_data='accept')
		decline_button = InlineKeyboardButton(text=decline_text, callback_data='decline')
		markup = InlineKeyboardMarkup()
		markup.row(accept_button, decline_button)

		message_id = await safe_edit_message(
			previous_message_id=previous_message_id,
			chat_id=chat_id,
			text=text,
			reply_markup=markup
		)

		await _save_waiting_for_flag(user_id, chat_id, waiting_for)

		# Пробуем получить ответ
		try:
			response = await asyncio.wait_for(fut, timeout)
		except asyncio.TimeoutError:
			logger.info("Timeout in request_confirmation for %s", key)
			await bot.edit_message_text(text='Время ввода истекло.', chat_id=chat_id, message_id=previous_message_id)
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=None)
			if delete_message_after:
				await delete_message_after_delay(chat_id=chat_id, message_id=previous_message_id, delay_seconds=1)
			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data.pop('waiting_for', None)
			return False
		finally:
			# Удаляем из ожидания
			await set_default_state(user_id, chat_id)
			awaiters.pop(key, None)

		# Если пользователь отменил
		if response is None:
			logger.info("User cancelled request_confirmation %s", key)
			return None
		# Если пользователь отклонил
		if isinstance(response, str):
			if 'decline' in response:
				logger.debug("User declined confirmation %s", key)
				return False
			# Если пользователь подтвердил
			elif 'accept' in response:
				logger.debug("User accepted confirmation %s", key)
				return True
		logger.warning("Unknown response in request_confirmation for %s: %s", key, response)
		return False
	finally:
		if delete_markup_after_choice:
			await safe_edit_message(
				previous_message_id=message_id,
				chat_id=chat_id,
				text=text,
				reply_markup=None
			)
		awaiters.pop(key, None)


async def request_files(
		user_id: int,
		chat_id: int,
		request_message: str = 'Отправьте файлы:',
		timeout: float = 60.0,
):
	key = (user_id, chat_id)
	if key in awaiters:
		logger.warning('Attempt to start request but already waiting for %s', key)
		raise RuntimeError('Already waiting for a response from the user')

	await _set_request_state(user_id, chat_id)
	await _save_waiting_for_flag(user_id, chat_id, 'file callback')

	# создаём очередь для этого запроса
	queue = asyncio.Queue()
	awaiters[key] = queue

	accept_button = InlineKeyboardButton('Подтвердить', callback_data='accept')
	decline_button = InlineKeyboardButton('Отменить', callback_data='cancel_files')
	markup = InlineKeyboardMarkup()
	markup.row(accept_button, decline_button)
	await bot.send_message(chat_id, text=request_message, parse_mode='HTML', reply_markup=markup)

	files = []
	try:
		while len(files) < 10:
			try:
				# ждём следующего элемента очереди с таймаутом
				response = await asyncio.wait_for(queue.get(), timeout)
			except asyncio.TimeoutError:
				logger.info("Timeout in request_files for %s", key)
				await send_temporary_message(chat_id, 'Время ввода истекло', delay_seconds=10)
				async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
					data.pop('waiting_for', None)
				return None

			# обработка элементов очереди
			# 1) если пришёл callback 'accept' или 'cancel_files' (строка)
			if isinstance(response, str):
				if response == 'accept':
					return files
				elif response == 'cancel_files':
					return 'cancel'
				else:
					# игнор/логирование неизвестной строки
					continue

			# 2) если пришло сообщение с файлом
			if response is None:
				return None
			else:
				try:
					file_type = getattr(response, 'content_type', None)
					if file_type is None or not file_type in ('document', 'photo'):
						logger.debug(f"Unsupported content_type: {getattr(response, 'content_type', None)}")
						return
					files.append((file_type, response))

				except Exception as e:
					logger.error(f"Can't save file from user ({user_id}): {e}")

			if len(files) >= 10:
				return files
	finally:
		await set_default_state(user_id, chat_id)
		awaiters.pop(key, None)


async def wait_for_callback_on_message(
		user_id: int,
		chat_id: int,
		message_id: int,
		timeout: float = 120.0,
		delete_callback_after=True
):
	specific_key = (user_id, chat_id, message_id)
	if specific_key in specific_awaiters and not specific_awaiters[specific_key].done():
		logger.warning('Attempting to wait for callback but already waiting for %s', specific_key)
		raise RuntimeError('Already waiting for a response from the user')

	await _save_waiting_for_flag(user_id, chat_id, 'callback')
	loop = asyncio.get_running_loop()
	fut = loop.create_future()
	specific_awaiters[specific_key] = fut

	try:
		try:
			response = await asyncio.wait_for(fut, timeout)
		except asyncio.TimeoutError:
			logger.info('Timeout waiting for specific callback %s', specific_key)
			async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
				data.pop('waiting_for', None)
			return None

		if response is None:
			logger.info('User cancelled specific callback %s', specific_key)
			return None
		return response
	finally:
		specific_awaiters.pop(specific_key, None)
		async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
			data.pop('waiting_for', None)
		if delete_callback_after:
			try:
				await bot.edit_message_reply_markup(
					chat_id=chat_id, message_id=message_id, reply_markup=None
				)
			except:
				logger.info("Can't delete markup on message %s", message_id)


@bot.message_handler(content_types=['photo', 'document'])
async def _handle_awaited_files(message):
	key = (message.from_user.id, message.chat.id)
	# убедимся, что мы действительно ожидаем файлы от этого чата
	async with bot.retrieve_data(key[0], key[1]) as data:
		if not data.get('waiting_for') or 'file' not in data.get('waiting_for', ''):
			return
	logger.info('Handle awaited file from %s', key)
	queue = awaiters.get(key)
	if queue is None:
		return

	try:
		# Кладём все сообщение как файл в очередь
		await queue.put(message)
	except asyncio.QueueFull:
		pass


# Принимает все кнопки от пользователя, который находится в ожидании
@bot.callback_query_handler(func=lambda call: (call.from_user.id, call.message.chat.id) in awaiters or (
call.from_user.id, call.message.chat.id, call.message.id) in specific_awaiters)
async def _handle_awaited_callback(call):
	await bot.answer_callback_query(call.id)
	key = (call.from_user.id, call.message.chat.id)

	# Получаем id сообщения из callback (совместимо с разными атрибутами)
	msg_id = getattr(call.message, 'message_id', None)
	if msg_id is None:
		msg_id = getattr(call.message, 'id', None)

	# Сначала пытаемся отдать результат специфическому ожидателю (user, chat, message)
	specific_key = (call.from_user.id, call.message.chat.id, msg_id)
	fut_specific = specific_awaiters.get(specific_key)
	if fut_specific is not None and not (isinstance(fut_specific, asyncio.Future) and fut_specific.done()):
		logger.info('Handle awaited specific callback from %s on message %s', key, msg_id)
		response = call.data
		# отмена
		if 'cancel' in response:
			try:
				fut_specific.set_result(None)
			except Exception:
				pass
			await send_temporary_message(call.message.chat.id, text='Ввод отменён', delay_seconds=2)
			return
		# ставим результат
		if hasattr(fut_specific, 'set_result'):
			try:
				fut_specific.set_result(response)
			except Exception:
				pass
		elif hasattr(fut_specific, 'put'):
			await fut_specific.put(response)
		return

	# fallback — существующее поведение для общих awaiters по (user, chat)
	logger.info('Handle awaited callback from %s', key)
	fut = awaiters.get(key)
	if fut is None or (isinstance(fut, asyncio.Future) and fut.done()):
		return
	response = call.data
	if response == 'cancel':
		try:
			if hasattr(fut, 'set_result'):
				fut.set_result(None)
			if hasattr(fut, 'put'):
				await fut.put(None)
		except Exception:
			pass
		await send_temporary_message(call.message.chat.id, text='Ввод отменён', delay_seconds=2)
	else:
		if hasattr(fut, 'set_result'):
			fut.set_result(response)
		elif hasattr(fut, 'put'):
			await fut.put(response)


# Принимает все сообщения от пользователя, который находится в ожидании
@bot.message_handler(content_types=['text'], func=lambda m: (m.from_user.id, m.chat.id) in awaiters)
async def _handle_awaited_answer(message):
	key = (message.from_user.id, message.chat.id)
	async with bot.retrieve_data(key[0], key[1]) as data:
		if not ('message' in data['waiting_for']):
			return
	logger.info('Handle awaited message from %s', key)
	fut = awaiters.get(key)
	if fut is None or (isinstance(fut, asyncio.Future) and fut.done()):
		return
	text = message.text.strip()
	if 'cancel' in text:
		fut.set_result(None)
		await send_temporary_message(message.chat_id, text='Ввод отменён', delay_seconds=2)
	else:
		if hasattr(fut, 'set_result'):
			logger.debug(f'Put result {message} in future')
			fut.set_result(message)
		elif hasattr(fut, 'put'):
			await fut.put(message)
