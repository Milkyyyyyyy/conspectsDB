"""
Обработчик callback'ов

"""

from telebot.callback_data import CallbackData

vote_cb = CallbackData('action', 'amount', prefix='vote')

call_factory = CallbackData('area', 'action', prefix='call')