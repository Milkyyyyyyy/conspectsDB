# TODO доделать end_registration

import asyncio
import os
import re
from dotenv import load_dotenv

from code.logging import logger

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.states.asyncio.middleware import StateMiddleware
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import asyncio_filters

from code.database.namespaced import getRowNamespaces
from code.database.queries import connectDB, isExists, getAll, get, insert

from datetime import datetime, timezone

load_dotenv()
TOKEN = os.getenv("API_KEY")
bot = AsyncTeleBot(TOKEN, state_storage=StateMemoryStorage())

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))


# State регситрации
class RegStates(StatesGroup):
    wait_for_name = State()
    wait_for_surname = State()
    wait_for_group = State()
    wait_for_facult = State()
    wait_for_chair = State()
    wait_for_direction = State()
    accept_registration = State()


# State главного меню
class MenuStates(StatesGroup):
    main_menu = State()

# Удаляет сообщение через некоторое количество времени
async def delete_message_after_delay(chat_id, message_id, delay_seconds=10):
    logger.debug(f'Delayed message deletion after {delay_seconds} seconds.')
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id, message_id)
        logger.debug(f'Message {message_id} deleted')
    except Exception as e:
        logger.warning(f'Failed to delete message {message_id} in chat {chat_id}\n {e}')
        pass
# Обрабатываем команду /start
@bot.message_handler(commands=['start'])
async def start(message):
    logger.info('The /start command has been invoked.')
    # Проверяем, существует ли пользователь
    user_id = str(message.from_user.id)
    database = connectDB()
    isUserExists, _ = isExists(database=database, table="USERS", filters={"telegram_id": user_id})
    database.close()
    # Если не существует, предлагаем пройти регистрацию
    if not isUserExists:
        logger.info(f'The user ({user_id}) does not exist')
        text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду /register или нажмите на кнопку ниже'
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Зарегистрироваться", callback_data="register"))
        await bot.reply_to(message, text, reply_markup=kb)
# Обрабатывает кнопки, в случаях, если они ничего не должны делать, и при необходимости выводит сообщение на экран
@bot.callback_query_handler(func=lambda call: 'empty' in call.data)
async def empty_button(call):
    data = call.data.split()
    if len(data) == 1:
        await bot.answer_callback_query(call.id)
    else:
        message = ' '.join(data[1:])
        await bot.answer_callback_query(call.id, text=message, show_alert=False)


# =================== Регистрация ===================
# Обработка команды кнопки регистрации
@bot.callback_query_handler(func=lambda call: call.data == 'register')
async def callback_start_register(call):
    logger.info(f'The registration button has been pressed (user_id = {call.from_user.id})')
    await bot.answer_callback_query(call.id)
    # Удаляем кнопку регистрации из сообщения (если не получилось, то ничего не делаем
    try:
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    await cmd_register(user_id=call.from_user.id, chat_id=call.message.chat.id)


# Обработка команды /register
@bot.message_handler(commands=['register'])
async def cmd_register(message=None, user_id=None, chat_id=None):
    logger.info('The /register command has been invoked')
    # Если на вход не подано user_id и chat_id, получаем эту информацию из объекта message
    if user_id is None:
        user_id = message.from_user.id
    if chat_id is None:
        chat_id = message.chat.id
    # Проверяем, существует ли пользователь
    db = connectDB()
    isUserExists, _ = isExists(database=db, table='USERS', filters={'telegram_id': str(user_id)})
    db.close()
    # Если пользователь найден, обрываем процесс регистрации
    if isUserExists:
        logger.info(f'The user ({user_id}) already exist. Stopping registration')
        await bot.send_message(chat_id, 'Вы уже зарегистрированы.')
        return
    else:
        async with bot.retrieve_data(user_id, chat_id) as data:
            data['table'] = 'FACULTS'
            data['page'] = 1
            data['filters'] = {}
            data['previous_message_id'] = None
        await bot.set_state(user_id, RegStates.wait_for_name, chat_id)
        await bot.send_message(chat_id, "Введите имя:")


# Сохранение имени пользователя
@bot.message_handler(state=RegStates.wait_for_name)
async def process_name(message=None):
    name = message.text
    if not re.fullmatch(r"^[А-Яа-яA-Za-z\-]{2,30}$", name):
        error_message = await bot.send_message(message.chat.id, "<b>Некорректное имя.</b>\n" 
                                                "Оно должно содержать <b>только буквы</b> (от 2 до 30).\n" 
                                                "Попробуйте ещё раз:", parse_mode='HTML')
        asyncio.create_task(delete_message_after_delay(message.chat.id, error_message.message_id, 4))
        asyncio.create_task(delete_message_after_delay(message.chat.id, message.id, 4))
        return
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name
    await bot.set_state(message.from_user.id, RegStates.wait_for_surname, message.chat.id)
    await bot.send_message(message.chat.id, "Введите фамилию:")


# Сохранение фамилии пользователя
@bot.message_handler(state=RegStates.wait_for_surname)
async def process_surname(message):
    surname = message.text
    if not re.fullmatch(r"^[А-Яа-яA-Za-z\-]{2,30}$", surname):
        error_message = await bot.send_message(message.chat.id, "<b>Некорректная фамилия.</b>\n"
                                            "Она должно содержать <b>только буквы</b> (от 2 до 30).\n"
                                            "Попробуйте ещё раз:\n", parse_mode='HTML')
        asyncio.create_task(delete_message_after_delay(message.chat.id, error_message.message_id, 4))
        asyncio.create_task(delete_message_after_delay(message.chat.id, message.id, 4))
        return
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['surname'] = surname
    await bot.set_state(message.from_user.id, RegStates.wait_for_group, message.chat.id)
    await bot.send_message(message.chat.id, "Из какой вы группы?")


# Сохранение группы пользователя
@bot.message_handler(state=RegStates.wait_for_group)
async def process_group(message):
    group = message.text
    if not re.fullmatch(r"^[А-Яа-я]{1,10}-\d{1,3}[А-Яа-я]?$", group):
        error_message = await bot.send_message(message.chat.id, "<b>Некорректный формат группы</b>\n"
                               "Ожидается что-то вроде <i>'ПИбд-12'</i> или <i>'МОАИСбд-11'</i>\n"
                               "Попробуйте ещё раз:", parse_mode='HTML')
        asyncio.create_task(await delete_message_after_delay(message.chat.id, error_message.message_id, 4))
        asyncio.create_task(await delete_message_after_delay(message.chat.id, message.id, 4))
        return
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['group'] = group
    await bot.set_state(message.from_user.id, RegStates.wait_for_facult, message.chat.id)
    await choose_direction(userID=message.from_user.id, chatID=message.chat.id)


# Обработка изменения страницы
@bot.callback_query_handler(func=lambda call: 'page' in call.data)
async def process_change_page_call(call):
    await bot.answer_callback_query(call.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['previous_message_id'] = call.message.message_id
        if 'next' in call.data:
            data['page'] += 1
        else:
            data['page'] -= 1
    await choose_direction(userID=call.from_user.id, chatID=call.message.chat.id)

# Обработка выбора пользователя
@bot.callback_query_handler(func=lambda call: 'next step' in call.data)
async def process_next_step_list(call):
    await bot.answer_callback_query(call.id)
    message = call.data.split()
    choice = message[2]
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        # Получаем rowid
        data[data['table']] = choice
        # Определяем следующую таблицу и фильтры
        match data['table']:
            case 'FACULTS':
                data['table'] = 'CHAIRS'
                data['filters'] = {'facult_id': int(choice)}
            case 'CHAIRS':
                data['table'] = 'DIRECTIONS'
                data['filters'] = {'chair_id': int(choice)}
            case 'DIRECTIONS':
                data['table'] = 'END_CHOOSING'
                data['filters'] = {}
        data['page'] = 1
        data['previous_message_id'] = call.message.message_id

    await choose_direction(userID=call.from_user.id, chatID=call.message.chat.id)


# Выводим список с выбором факультета, кафедры и направления
async def choose_direction(userID=None, chatID=None):
    # Получаем из даты информацию о текущей странице и таблице
    async with bot.retrieve_data(userID, chatID) as data:
        # Пробуем получить информации из data. Если её нет - записываем дефолтную
        try:
            table = data['table']
            if table == 'END_CHOOSING':
                await accept_registration(user_id=userID, chat_id=chatID)
                return
        except:
            data['table'] = 'FACULTS'
            table = 'FACULTS'
        try:
            previous_message_id = data['previous_message_id']
        except:
            previous_message_id = None
        try:
            page = data['page']
        except:
            data['page'] = 1
            page = 1
        try:
            filters = data['filters']
        except:
            data['filters'] = {}
            filters = {}

    # Получаем список из таблицы
    database = connectDB()
    all_list, cursor = getAll(database=database, table=table, filters=filters)
    database.close()

    # Определяем текущий индекс, последний индекс
    MAX_ELEMENTS_PER_PAGE = 6
    ELEMENTS_PER_ROW = 2
    max_page = max(len(all_list) // MAX_ELEMENTS_PER_PAGE, 1)
    if page > max_page:
        page = max_page
    current_index = (page - 1) * MAX_ELEMENTS_PER_PAGE
    max_index = min(len(all_list), current_index + MAX_ELEMENTS_PER_PAGE)

    # Собираем кнопки
    new_row = []
    markup = InlineKeyboardMarkup()
    for ind in range(current_index, max_index):
        row = all_list[ind]
        ns = getRowNamespaces(row=row, cursor=cursor)
        button = InlineKeyboardButton(ns.name, callback_data=f"next step {ns.rowid}")
        new_row.append(button)
        if len(new_row) >= ELEMENTS_PER_ROW:
            markup.row(*new_row)
            new_row = []
    # Кнопки перемещения страниц
    next_page_button = InlineKeyboardButton("--->", callback_data='empty' if page == max_page else 'next page')
    previous_page_button = InlineKeyboardButton("<---", callback_data='empty' if page == 1 else 'previous page')
    question_button = InlineKeyboardButton("Не могу найти", callback_data='message moderator')
    markup.row(previous_page_button, next_page_button)

    # Собираем текст сообщения
    table_text = ''
    match table:
        case 'FACULTS':
            table_text = 'факультет'
        case 'CHAIRS':
            table_text = 'кафедру'
        case 'DIRECTIONS':
            table_text = 'направление'
    message_text = f"🔎 Выберите {table_text}\nСтр. {page} из {max_page}"

    # Выводим сообщение (если есть previous_message_id - меняем старое)
    if previous_message_id is None:
        await bot.send_message(chatID, message_text, reply_markup=markup)
    else:
        await bot.edit_message_text(message_text, chatID, previous_message_id)
        await bot.edit_message_reply_markup(chatID, previous_message_id, reply_markup=markup)


# Выводит сообщение, чтобы пользователь проверил правильность данных
# Если всё правильно -> переходим в end_register, где сохраняем всю нужную информацию в датабазу
# Если нет, просто заново начинаем процесс регистрации
async def get_registration_info(user_id=None, chat_id=None):
    async with bot.retrieve_data(user_id, chat_id) as data:
        name = data['name']
        surname = data['surname']
        group = data['group']
        direction_id = data['DIRECTIONS']
    database = connectDB()
    direction, cursor = get(database=database, table='DIRECTIONS', filters={'rowid': direction_id})
    direction_ns = getRowNamespaces(row=direction, cursor=cursor)

    chair, cursor = get(database=database, table='CHAIRS', filters={'rowid': direction_ns.chair_id})
    chair_ns = getRowNamespaces(row=chair, cursor=cursor)

    facult, cursor = get(database=database, table='FACULTS', filters={'rowid': chair_ns.facult_id})
    facult_ns = getRowNamespaces(row=facult, cursor=cursor)
    database.close()
    return name, surname, group, facult_ns, chair_ns, direction_ns

# Проверяем у пользователя правильность информации. Если нет - начинаем регистрацию заново
async def accept_registration(user_id=None, chat_id=None):
    async with bot.retrieve_data(user_id, chat_id) as data:
        try:
            await bot.delete_message(chat_id, data['previous_message_id'])
        except Exception:
            pass
    name, surname, group, facult_ns, chair_ns, direction_ns = await get_registration_info(user_id=user_id, chat_id=chat_id)

    # Собираем кнопки
    buttons = InlineKeyboardMarkup()
    buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
    buttons.add(InlineKeyboardButton("Повторить регистрацию", callback_data="register"))
    await bot.send_message(chat_id,
                           f"Проверьте правильность данных\n\n"
                           f"<blockquote><b>Имя</b>: {name}\n"
                           f"<b>Фамилия</b>: {surname}\n"
                           f"<b>Учебная группа</b>: {group}\n\n"
                           f"<b>Факультет</b>: {facult_ns.name}\n"
                           f"<b>Кафедра</b>: {chair_ns.name}\n"
                           f"<b>Направление</b>: {direction_ns.name}</blockquote>\n",
                           reply_markup=buttons, parse_mode='HTML')

# Сохраняем информацию в датабазу
@bot.callback_query_handler(func=lambda call: call.data == 'registration_accepted')
async def end_registration(call):
    logger.info('Registration accepted.')
    await bot.answer_callback_query(call.id)
    message = await bot.send_message(call.message.chat.id, 'Завершаю регистрацию...')
    try:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception:
        pass
    # Сохраняем информацию в датабазу
    logger.info('Saving user in database.')
    name, surname, group, _, _, direction_ns = await get_registration_info(call.from_user.id, call.message.chat.id)

    # Добавляю запись в датабазу
    db = connectDB()
    values  = [str(call.from_user.id), name,   surname,   group,         direction_ns.rowid, 'user']
    columns = ['telegram_id',         'name', 'surname', 'study_group', 'direction_id',      'role']
    insert(database=db, table = 'USERS', values=values, columns=columns)
    # db.commit()
    db.close()
    await bot.edit_message_text('Готово!', call.message.chat.id, message.message_id)
    logger.info('Successfully saved user in database.')
    await bot.set_state(call.from_user.id, MenuStates.main_menu, call.message.chat.id)

# Логирование всех обновлений (например, сообщений от пользователя)
async def log_updates(updates):
    for upd in updates:
        # Я как понял, в старых версиях upd был объектом со множеством подобъектов. Но сейчас это просто Message
        # Но на всякий случай сделаю try-except
        try:
            msg = upd.message
        except:
            msg = upd
        if not msg: continue
        logger.debug("%s | %s | %s | %s", datetime.now(timezone.utc).isoformat(),
                    msg.from_user.id, msg.from_user.username, msg.text)
async def main():
    try:
        logger.info("Starting polling...")
        bot.set_update_listener(log_updates)
        await bot.infinity_polling()
    finally:
        # гарантированно закрываем сессию aiohttp, чтобы не было "Unclosed client session"
        try:
            if hasattr(bot, "session") and bot.session:
                await bot.session.close()
                logger.debug("bot.session closed")
        except Exception as e:
            logger.exception("End session %s", e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user (KeyboardInterrupt)")
