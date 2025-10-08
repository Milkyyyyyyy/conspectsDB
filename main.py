from code.logging import logger
from code.database.repo.queries import connectDB, Tables, get, getAll, isExists, insert, remove, removeList
from code.database.classes.namespaced import *
# from code.bot import mainBot

logger.info("Starts application...")
database = connectDB()
allRows = getAll(database=database, table="CHAIRS")
print(allRows)

response, cursor = get(database=database, table="CHAIRS", filters = {"rowid": 2})
ns = getRowNamespaces(cursor, response)
database.close()