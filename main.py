from code.logging import logger
from code.database.repo.queries import getAll, get, connectDB, insert
from code.database.classes.namespaced import getRowNamespaces

logger.info("Starts application...")
database = connectDB()
response, cursor = getAll(database=database, table="CHAIRS")
print(response)

response = getAll(database=database, table="CHAIRS", filters={"name": "Имя"})
print(response)
database.commit()
database.close()

# from code.bot import mainBot