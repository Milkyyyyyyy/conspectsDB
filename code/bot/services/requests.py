from code.bot.bot_instance import bot
import asyncio

awaiters: dict[tuple[int, int], asyncio.Future] = {}
async def request(user_id, chat_id, timeout=60.0, request_message='Введите:', waiting_for='temp'):
	key = (user_id, chat_id)

	if key in awaiters and not awaiters[key].done():
		raise RuntimeError('Already waiting for a response from the user')

	loop = asyncio.get_event_loop()
	fut = loop.create_future()
	awaiters[key] = fut

	await bot.send_message(chat_id, request_message)
	async with bot.retrieve_data(user_id, chat_id) as data:
		data['waiting_for'] = waiting_for
	try:
		name = await asyncio.wait_for(fut, timeout)
		async with bot.retrieve_data(user_id, chat_id) as data:
			data[waiting_for] = name
			data.pop('waiting_for', None)
		return name
	except asyncio.TimeoutError:
		await bot.send_message(chat_id, "Время на ввод истекло")
		async with bot.retrieve_data(user_id, chat_id) as data:
			data.pop('waiting_for', None)
	finally:
		await awaiters.pop(key, None)
@bot.message_handler(func=lambda m: (m.from_user.id, m.chat.id) in awaiters)
async def _handle_awaited_answer(message):
	key = (message.from_user.id, message.chat.id)
	fut = awaiters.get(key)
	if fut is None or fut.done():
		return
	text = message.text.strip()
	fut.set_result(text)