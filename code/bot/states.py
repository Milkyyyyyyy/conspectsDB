from telebot.asyncio_handler_backends import State, StatesGroup

# State регистрации
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