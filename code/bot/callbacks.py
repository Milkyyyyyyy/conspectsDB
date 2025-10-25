"""
Обработчик callback'ов

TODO Здесь ещё много надо будет сделать. И не только здесь
"""

from telebot.callback_data import CallbackData

vote_cb = CallbackData('action', 'amount', prefix='vote')
