import logging
import os
import sys

file_path = "logs/app.log"
os.makedirs(os.path.dirname(file_path), exist_ok=True)  # создаём папку logs, если её нет

if not os.path.exists(file_path):
    open(file_path, "w").close()



logging.basicConfig(
	# filename=file_path,
	stream=sys.stdout,
	level=logging.INFO,
	format=u"[%(asctime)s] - %(levelname)-13s %(funcName)-15s:%(lineno)-4d ⇨ %(message)s",
	datefmt='%Y-%m-%d %H:%M:%S',
	encoding='utf-8'

)
logger = logging.getLogger(__name__)
