import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
	filename='logs/app.log',
	level=logging.DEBUG,
	format='[%(asctime)s] - %(levelname)s - %(name)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)
