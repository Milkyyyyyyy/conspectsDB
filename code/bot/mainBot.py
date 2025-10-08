import asyncio
from code.database.repo.queries import connectDB, isExists
from telebot.async_telebot import AsyncTeleBot

API_TOKEN: str = '7428239168:AAHTx5DadgqK4Q7oKmhlBJkwAW9iRYHcaso'
bot = AsyncTeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    userID= str(message.from_user.id)
    database = connectDB()
    isUserExists, _ = isExists(database=database, table="USERS", filters={"telegram_id": userID})
    database.close()
    print(isUserExists)
    if not isUserExists:
        text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду `register`'
        await bot.reply_to(message, text)

@bot.message_handler(commands=['register'])
async def registerUser(message):
    chatID = message.chat.id
    userID= str(message.from_user.id)
    database=connectDB()
    isUserExists, _ = isExists(database=database, table="USERS", filters={"telegram_id": userID})
    if isUserExists:
        await bot.send("Похоже, вы уже зарегистрированы")
        return
    else:
        await bot.send_message(chatID, "Запускаю процесс регистрации...")
        # name = bot.register_next_step_handler(message, registerUser)
        # await bot.send_message(chatID, name)
    database.close()

# async def getName(message):
#     chatID = message.chat.id
#     await bot.send_message(chatID, "Введи своё имя")
#     userName = message.text
#     await bot.send_message(chatID, f"Приятно познакомиться, {userName}")
#     return userName
# asyncio.run(bot.infinity_polling())