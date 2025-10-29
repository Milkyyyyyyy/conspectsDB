import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
	filename='logs/app.log',
	level=logging.DEBUG,
	format='[%(asctime)s] - %(levelname)s %(funcName)s:%(lineno)d -- %(message)s',

	datefmt='%Y-%m-%d %H:%M:%S'
)
