import asyncio

from telebot.async_telebot import AsyncTeleBot

API_TOKEN: str = '7428239168:AAHTx5DadgqK4Q7oKmhlBJkwAW9iRYHcaso'
bot = AsyncTeleBot(API_TOKEN)

@bot.message_handler(commands=['help', 'start'])
async def send_welcome(message):
    text = 'TEST BOT ANSWER'
    await bot.reply_to(message, text)

asyncio.run(bot.polling())