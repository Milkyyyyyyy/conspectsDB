import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='logs/app.log',
    level=logging.DEBUG,
    format='[%(asctime)s] - %(levelname)s - %(wait_for_name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)