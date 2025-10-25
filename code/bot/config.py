"""
Прочее, не связанное напрямую с ботом (различные переменные среды и т.д)
"""

import os

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("API_KEY")
