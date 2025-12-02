"""
Module for working with user conspects in a Telegram bot.

Provides functionality for viewing, navigating, and deleting user conspects
with pagination and interactive buttons support.
"""

# TODO: Split the logic of generating formatted text
# list of conspects into different functions and move part to services.conspects.py

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import wait_for_callback_on_message, request_confirmation
from code.bot.utils import safe_edit_message
from code.logging import logger
from code.bot.callbacks import call_factory
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiException, ApiHTTPException
from code.database.service import connect_db
from code.database.queries import get, get_all
from typing import List, Dict, Optional, Tuple
import math
import asyncio
from code.bot.services.conspects import (
    make_list_of_conspects,
    generate_list_markup,
    get_conspects_list_slice,
    send_conspect_message,
    delete_conspect,
    get_all_subjects
)


@bot.callback_query_handler(func=call_factory.filter(area='user_conspects').check)
async def callback_handler(call) -> None:
    """
    Main handler for callback queries in the 'user_conspects' area.

    :param call: CallbackQuery object from Telegram API
    :return: None
    """
    logger.info(
        'Received callback in user_conspects from user user_id=%s, '
        'username=%s, chat_id=%s',
        call.from_user.id,
        call.from_user.username,
        call.message.chat.id
    )

    # Extract user data from callback
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id
    username = call.from_user.username

    # Confirm callback receipt (removes "clock" in Telegram)
    try:
        await bot.answer_callback_query(call.id)
        logger.debug('Callback query successfully confirmed for user_id=%s', user_id)
    except ApiException as e:
        logger.error(
            'Telegram API error when answering callback query for user_id=%s: %s',
            user_id, str(e)
        )
        return
    except Exception as e:
        logger.exception(
            'Unexpected error when answering callback query for user_id=%s',
            user_id
        )
        return

    # Parse action from callback_data
    try:
        action = call_factory.parse(callback_data=call.data)['action']
        logger.debug('Recognized action=%s for user_id=%s', action, user_id)
    except (KeyError, ValueError, TypeError) as e:
        logger.error(
            'Error parsing callback_data="%s" for user_id=%s: %s',
            call.data, user_id, str(e)
        )
        return

    # Action routing
    match action:
        case 'user_conspects':
            try:
                await user_conspect(user_id, chat_id)
            except Exception as e:
                logger.exception(
                    'Critical error when processing user_conspects for user_id=%s',
                    user_id
                )


async def print_user_conspects(
    user_id: int,
    chat_id: int,
    conspects_list: Optional[List[Dict]] = None,
    conspects_per_page: int = 10,
    page: int = 1
) -> None:
    """
    Displays a list of user conspects with pagination and navigation.

    :param user_id: Telegram user ID
    :param chat_id: Chat ID for sending messages
    :param conspects_list: List of conspects from DB (None if no conspects)
    :param conspects_per_page: Number of conspects per page
    :param page: Initial page to display
    :return: None
    """
    logger.info(
        'Displaying conspects for user_id=%s, page=%d, '
        'conspects_count=%d',
        user_id, page, len(conspects_list) if conspects_list else 0
    )

    # Initialize markup and count conspects
    markup = InlineKeyboardMarkup()
    conspects_amount = 0 if conspects_list is None else len(conspects_list)

    # Form list header
    rule_line = '───────────────────────────\n'
    header = (
        f'📚 ВАШИ КОНСПЕКТЫ ({conspects_amount})\n'
        '🔍 Фильтр: Все предметы\n\n'
    ) + rule_line

    # Handle case when there are no conspects
    if not conspects_list:
        logger.info('User user_id=%s has no conspects', user_id)
        back_button = InlineKeyboardButton(
            'Назад в меню',
            callback_data=call_factory.new(
                area='main_menu',
                action='main_menu'
            )
        )
        markup.row(back_button)
        text = header + '\n\n📭 У вас пока нет конспектов!'

        try:
            await bot.send_message(chat_id, text=text, reply_markup=markup)
            logger.debug('No conspects message sent to user_id=%s', user_id)
        except ApiException as e:
            logger.error(
                'Error sending no conspects message to user_id=%s: %s',
                user_id, str(e)
            )
            return
        except Exception as e:
            logger.exception(
                'Unexpected error when sending message to user_id=%s',
                user_id
            )
            return
        return

    # Calculate total number of pages
    last_page = math.ceil(conspects_amount / conspects_per_page)
    logger.debug('Total pages=%d, conspects=%d', last_page, conspects_amount)

    # Create navigation buttons
    back_button = InlineKeyboardButton('Назад в меню', callback_data='back')
    next_page_button = InlineKeyboardButton('--->', callback_data='next_page')
    previous_page_button = InlineKeyboardButton('<---', callback_data='previous_page')

    # State variables for processing loop
    response = ''
    update_markup = True
    update_conspect_list = True
    previous_message_id = None

    # Generate formatted conspects list
    try:
        conspects_formatted_list, conspect_by_index = await make_list_of_conspects(conspects_list)
        logger.debug('Conspects list formatted for user_id=%s', user_id)

        # Get all subjects (for future filter)
        subjects = await get_all_subjects(conspects_list)
        logger.debug('Found %d unique subjects for user_id=%s', len(subjects), user_id)
    except Exception as e:
        logger.exception('Error formatting conspects list for user_id=%s', user_id)
        return

    # Main loop for user interaction processing
    while response != 'back':
        try:
            # Update conspects list if necessary
            if update_conspect_list:
                logger.debug('Updating conspects list for user_id=%s', user_id)
                conspects_formatted_list, conspect_by_index = await make_list_of_conspects(conspects_list)
                update_conspect_list = False

            # Calculate indices for current page
            first_index = (page - 1) * conspects_per_page
            last_index = min(first_index + conspects_per_page, conspects_amount)
            logger.debug(
                'Displaying page %d: indices %d-%d for user_id=%s',
                page, first_index, last_index, user_id
            )

            # Form message text for current page
            message_text = await get_conspects_list_slice(
                header,
                rule_line,
                conspects_formatted_list,
                first_index,
                last_index,
                page,
                last_page
            )

            # Update keyboard if necessary
            if update_markup:
                logger.debug('Updating keyboard markup for user_id=%s', user_id)
                markup = await generate_list_markup(first_index, last_index)
                markup.row(previous_page_button, next_page_button)
                markup.row(back_button)

            # Send/edit message with list
            try:
                previous_message_id = await safe_edit_message(
                    previous_message_id=previous_message_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    text=message_text,
                    reply_markup=markup
                )
                update_markup = False
                logger.debug('List message updated for user_id=%s', user_id)
            except Exception as e:
                logger.error('Error editing message for user_id=%s: %s', user_id, str(e))
                break

            # Wait for user response (timeout 2 minutes)
            response = await wait_for_callback_on_message(
                user_id,
                chat_id,
                message_id=previous_message_id,
                timeout=60 * 2,
                delete_callback_after=False
            )

            # Handle timeout (user didn't respond)
            if response is None:
                logger.info('Timeout waiting for response from user_id=%s', user_id)
                response = 'back'
                continue

            logger.debug('Received response="%s" from user_id=%s', response, user_id)

            # Handle selection of specific conspect
            if 'conspect' in response:
                try:
                    conspect_index = int(response.split()[-1])
                    logger.info(
                        'User user_id=%s selected conspect with index=%d',
                        user_id, conspect_index
                    )
                    await print_conspect_by_index(
                        user_id,
                        chat_id,
                        conspect_by_index,
                        conspect_index,
                        previous_message_id
                    )
                    update_markup = True
                except (ValueError, IndexError) as e:
                    logger.error(
                        'Error parsing conspect index from response="%s" for user_id=%s: %s',
                        response, user_id, str(e)
                    )
            else:
                # Handle navigation commands
                match response:
                    case 'next_page':
                        if page < last_page:
                            page += 1
                            update_markup = True
                            logger.debug('Moving to page %d for user_id=%s', page, user_id)
                        else:
                            logger.debug('Attempted to go past last page for user_id=%s', user_id)

                    case 'previous_page':
                        if page > 1:
                            page -= 1
                            update_markup = True
                            logger.debug('Moving to page %d for user_id=%s', page, user_id)
                        else:
                            logger.debug('Attempted to go before first page for user_id=%s', user_id)

                    case 'back':
                        logger.info('User user_id=%s is returning to main menu', user_id)
                        # Remove buttons to avoid repeated clicks
                        try:
                            await bot.edit_message_reply_markup(
                                chat_id,
                                previous_message_id,
                                reply_markup=None
                            )
                            logger.debug('Keyboard removed for user_id=%s', user_id)
                        except ApiException as e:
                            logger.warning(
                                'Failed to remove keyboard for user_id=%s: %s',
                                user_id, str(e)
                            )
                        except Exception as e:
                            logger.exception(
                                'Unexpected error when removing keyboard for user_id=%s',
                                user_id
                            )

                        # Async transition to main menu
                        asyncio.create_task(main_menu(user_id, chat_id))
                        return

        except Exception as e:
            logger.exception(
                'Critical error in conspects list processing loop for user_id=%s',
                user_id
            )
            break


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
    delete_button = InlineKeyboardButton('Удалить конспект', callback_data='delete_conspect')
    markup = InlineKeyboardMarkup()
    markup.row(back_button)
    markup.row(delete_button)

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
                timeout=10
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
                    # Delete messages with conspect
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

                case 'delete_conspect':
                    logger.info(
                        'Conspect deletion request index=%d from user_id=%s',
                        conspect_index, user_id
                    )
                    # Request deletion confirmation
                    try:
                        confirm = await request_confirmation(
                            user_id,
                            chat_id,
                            'Вы уверены, что хотите удалить конспект?'
                        )
                    except Exception as e:
                        logger.error(
                            'Error requesting deletion confirmation for user_id=%s: %s',
                            user_id, str(e)
                        )
                        continue

                    # Delete conspect upon confirmation
                    if confirm:
                        logger.info('Conspect deletion confirmed by user_id=%s', user_id)
                        try:
                            await delete_conspect(conspect_row=conspect)
                            logger.info(
                                'Conspect successfully deleted: index=%d, user_id=%s',
                                conspect_index, user_id
                            )
                        except Exception as e:
                            logger.exception(
                                'Error deleting conspect for user_id=%s',
                                user_id
                            )
                            continue

                        # Delete all related messages
                        message_id_to_delete = previous_message_id + 1
                        deleted_count = 0

                        while True:
                            await asyncio.sleep(0.25)  # Small delay between deletions
                            try:
                                await bot.delete_message(chat_id, message_id_to_delete)
                                deleted_count += 1
                                message_id_to_delete += 1
                            except ApiException as e:
                                logger.debug(
                                    'Reached end of messages to delete (user_id=%s): %s',
                                    user_id, str(e)
                                )
                                break
                            except Exception as e:
                                logger.warning(
                                    'Error deleting message id=%d for user_id=%s: %s',
                                    message_id_to_delete, user_id, str(e)
                                )
                                break

                        logger.info(
                            'Deleted %d messages after conspect deletion for user_id=%s',
                            deleted_count, user_id
                        )
                        return
                    else:
                        logger.info('Conspect deletion cancelled by user_id=%s', user_id)

        except Exception as e:
            logger.exception(
                'Critical error when displaying conspect for user_id=%s',
                user_id
            )
            break


async def user_conspect(user_id: int, chat_id: int) -> None:
    """
    Main function for retrieving and displaying user conspects.
    Executes a DB query to get all user conspects and passes them to the display function.

    :param user_id: Telegram user ID
    :param chat_id: Chat ID for sending messages
    :return: None
    """
    logger.info('Requesting conspects from DB for user_id=%s', user_id)

    try:
        # Connect to DB and get conspects
        async with connect_db() as db:
            logger.debug('DB connection established for user_id=%s', user_id)
            conspects = await get_all(
                database=db,
                table='CONSPECTS',
                filters={'user_telegram_id': user_id}
            )
            conspects.sort(key= lambda x: x['upload_date'])
            logger.info(
                'Retrieved %d conspects from DB for user_id=%s',
                len(conspects) if conspects else 0, user_id
            )
    except Exception as e:
        logger.exception('Error retrieving conspects from DB for user_id=%s', user_id)
        # Send error message to user
        try:
            await bot.send_message(
                chat_id,
                '❌ Произошла ошибка при загрузке конспектов. Попробуйте позже.'
            )
        except Exception as send_error:
            logger.error(
                'Failed to send error message to user_id=%s: %s',
                user_id, str(send_error)
            )
        return

    # Display retrieved conspects
    try:
        await print_user_conspects(user_id, chat_id, conspects_list=conspects)
    except Exception as e:
        logger.exception('Error displaying conspects for user_id=%s', user_id)
