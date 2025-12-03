import logging

logging.basicConfig(
	filename='logs/app.log',
	level=logging.INFO,
	format=u"[%(asctime)s] - %(levelname)-13s %(funcName)-15s:%(lineno)-4d ⇨ %(message)s",
	datefmt='%Y-%m-%d %H:%M:%S',
	encoding='utf-8'
)
logger = logging.getLogger(__name__)
