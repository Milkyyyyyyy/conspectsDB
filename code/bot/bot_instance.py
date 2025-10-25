from dotenv import load_dotenv
import os
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.states.asyncio.middleware import StateMiddleware
from telebot import asyncio_filters
from code.bot.config import TOKEN

bot = AsyncTeleBot(TOKEN, state_storage=StateMemoryStorage())
bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))