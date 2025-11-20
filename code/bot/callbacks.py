"""
Обработчик callback'ов

"""

from telebot.callback_data import CallbackData

call_factory = CallbackData('area', 'action', prefix='call')
