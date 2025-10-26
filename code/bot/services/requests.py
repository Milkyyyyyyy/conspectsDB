from code.bot.bot_instance import bot
from code.bot.utils import send_temporary_message, delete_message_after_delay
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


