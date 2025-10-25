from code.bot.bot_instance import bot

@bot.callback_query_handler(func=lambda call: 'empty' in call.data)
async def empty_button(call):
	data = call.data.split()
	if len(data) == 1:
		await bot.answer_callback_query(call.id)
	else:
		message = ' '.join(data[1:])
		await bot.answer_callback_query(call.id, text=message, show_alert=False)