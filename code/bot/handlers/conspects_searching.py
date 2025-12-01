from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.services.requests import wait_for_callback_on_message, request_confirmation, request
from code.bot.utils import safe_edit_message
from code.database.service import connect_db
from code.database.queries import get, get_all
from code.bot.services.conspects import *
from telebot.apihelper import ApiException, ApiHTTPException, edit_message_reply_markup
import math
from typing import Dict, Optional
from code.searching import *

@bot.callback_query_handler(func=call_factory.filter(area='conspects_searching').check)
async def callback_handler(call):
	logger.debug('Handle callback in conspects_searching...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', user_id, exc_info=e)

	action = call_factory.parse(callback_data=call.data)['action']

	match action:
		case 'conspects_searching':
			await conspect_searching(user_id, chat_id)

async def update_conspect_row(filters={}, query=None):
	async with connect_db() as db:
		conspects = await get_all(
			database=db,
			table='CONSPECTS',
			filters=filters
		)
		conspect_dicts = []
		for conspect in conspects:
			conspect_dicts.append(await safe_row_to_dict(conspect))
		all_subjects_names = []

		for i, conspect in enumerate(conspect_dicts):
			subject = await get(database=db,
			                    table='SUBJECTS',
			                    filters={'rowid': conspect['subject_id']})
			conspect_dicts[i]['subject_name'] = subject['name']

	if query is not None:
		conspect_dicts = await search_and_rank(
			conspect_dicts,
			query,
			keys = ('theme', 'keywords', 'subject_name')
		)
	return conspect_dicts
async def update_conspect_info(all_conspects_rows, page, conspects_per_page, filters={}):
	# filters['status'] = 'accepted'

	conspects_amount = len(all_conspects_rows)
	last_page = math.ceil(conspects_amount / conspects_per_page)
	formatted_list, conspects_by_index = await make_list_of_conspects(all_conspects_rows)

	first_index = (page - 1) * conspects_per_page
	last_index = min(first_index + conspects_per_page, conspects_amount)
	return (conspects_amount,
	        last_page,
	        formatted_list,
	        conspects_by_index,
	        first_index,
	        last_index)
async def conspect_searching(
		user_id,
		chat_id,
		page=1,
		conspects_per_page=10,
		header=''
):


	back_button = InlineKeyboardButton('Назад в меню', callback_data='back')
	next_page_button = InlineKeyboardButton('--->', callback_data='next_page')
	previous_page_button = InlineKeyboardButton('<---', callback_data='previous_page')
	set_filter_button = InlineKeyboardButton('🔍 Поиск', callback_data='set_filter')


	all_conspects_rows = await update_conspect_row()
	(conspects_amount,
	 last_page, formatted_list,
	 conspects_by_index,
	 first_index,
	 last_index) = await update_conspect_info(all_conspects_rows, page, conspects_per_page)
	users_query = None
	rule_line = '───────────────────────────\n'
	header = (
		         f'📚 ПОЛЬЗОВАТЕЛЬСКИЕ КОНСПЕКТЫ ({conspects_amount})\n'
		         '🔍 Фильтр: Все предметы\n'
		         f'{'' if users_query is None else f'Запрос: {users_query}\n'}'
	         ) + rule_line



	update_conspect = True
	update_message_text = True
	response = ''
	previous_message_id = None
	while response != 'back':
		if update_conspect:
			all_conspects_rows = await update_conspect_row(query=users_query)
			update_conspect = False
			update_message_text = True
		if update_message_text:
			(conspects_amount,
			 last_page, formatted_list,
			 conspects_by_index,
			 first_index,
			 last_index) = await update_conspect_info(all_conspects_rows, page, conspects_per_page)
			rule_line = '───────────────────────────\n'
			header = (
				         f'<b>📚 ПОЛЬЗОВАТЕЛЬСКИЕ КОНСПЕКТЫ ({conspects_amount})</b>\n'
				         '<b>🔍 Фильтр:</b> <i>Все предметы</i>\n'
				         f'{'' if users_query == '' else f'<b>Запрос:</b> <i>{users_query}</i>\n\n'}'
			         ) + rule_line
			message_text = await get_conspects_list_slice(
				header,
				rule_line,
				formatted_list,
				first_index,
				last_index,
				page,
				last_page
			)
			markup = await generate_list_markup(
				first_index,
				last_index
			)
			markup.row(previous_page_button, set_filter_button, next_page_button)
			markup.row(back_button)
			previous_message_id = await safe_edit_message(
				previous_message_id,
				chat_id,
				user_id,
				text=message_text,
				reply_markup=markup
			)
			update_message_text = False

		response = await wait_for_callback_on_message(
			user_id,
			chat_id,
			previous_message_id,
			timeout=60*2,
			delete_callback_after=False
		)
		if response is None:
			response = 'back'
		if 'conspect' in response:
			conspect_index = int(response.split()[-1])
			await print_conspect_by_index(user_id,
			                              chat_id,
			                              conspects_by_index, conspect_index)
			update_conspect = True
		else:
			match response:
				case 'back':
					try:
						await bot.edit_message_reply_markup(
							chat_id,
							previous_message_id,
							reply_markup=None
						)
					except:
						logger.exception("Can't delete markup")
					asyncio.create_task(main_menu(user_id, chat_id))
					return
				case 'next_page':
					if page != last_page:
						page+=1
						update_message_text=True
				case 'previous_page':
					if page > 1:
						page-=1
						update_message_text=True
				case 'set_filter':
					users_query, request_message_id = await request(
						user_id,
						chat_id,
						request_message='Введите запрос\nНапишите "-" для очистки запроса'
					)
					if users_query == '-':
						users_query = None
					try:
						await bot.delete_message(chat_id, request_message_id)
						await bot.delete_message(chat_id, request_message_id+1)
					except:
						logger.exception("Can't delete messages")
					update_conspect = True


async def print_conspect_by_index(
    user_id: int,
    chat_id: int,
    conspects_by_index: Dict[int, Dict],
    conspect_index: int,
    previous_message_id: Optional[int] = None
) -> None:
    """
    Displays full information about a specific conspect by its index.

    :param user_id: Telegram user ID
    :param chat_id: Chat ID for sending messages
    :param conspects_by_index: Dictionary {index: conspect data}
    :param conspect_index: Index of the selected conspect
    :param previous_message_id: ID of previous message for deletion
    :return: None
    """
    logger.info(
        'Displaying conspect with index=%d for user_id=%s',
        conspect_index, user_id
    )

    # Check if conspect with given index exists
    if conspect_index not in conspects_by_index:
        logger.error(
            'Conspect with index=%d not found for user_id=%s',
            conspect_index, user_id
        )
        return

    # Create control buttons
    back_button = InlineKeyboardButton('Назад к конспектам', callback_data='back')
    markup = InlineKeyboardMarkup()
    markup.row(back_button)

    # Get conspect data
    conspect = conspects_by_index[conspect_index]
    logger.debug('Conspect data retrieved: %s', conspect['theme'])

    response = ''

    # Loop for handling actions with conspect
    while response != 'back':
        try:
            # Send message with conspect
            message = await send_conspect_message(
                user_id,
                chat_id,
                conspect_row=conspect,
                reply_markup=markup,
                markup_text='Выберите действие'
            )
            logger.debug('Conspect message sent to user_id=%s', user_id)

            # Wait for user action (timeout 10 seconds)
            response = await wait_for_callback_on_message(
                user_id,
                chat_id,
                message_id=message.id,
                timeout=60*2
            )

            # Handle timeout
            if response is None:
                logger.info('Timeout when viewing conspect for user_id=%s', user_id)
                response = 'back'
                continue

            logger.debug('Received response="%s" when viewing conspect for user_id=%s', response, user_id)

            # Handle actions
            match response:
                case 'back':
                    logger.info('Returning to conspects list for user_id=%s', user_id)
                    try:
                        await bot.delete_message(chat_id, message.id)
                        await bot.delete_message(chat_id, message.id - 1)
                        logger.debug('Conspect messages deleted for user_id=%s', user_id)
                    except ApiException as e:
                        logger.warning(
                            'Failed to delete conspect messages for user_id=%s: %s',
                            user_id, str(e)
                        )
                    except Exception as e:
                        logger.exception(
                            'Unexpected error when deleting messages for user_id=%s',
                            user_id
                        )
                    return

        except Exception as e:
            logger.exception(
                'Critical error when displaying conspect for user_id=%s',
                user_id
            )
            break