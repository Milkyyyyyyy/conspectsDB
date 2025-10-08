from code.database.repo.queries import connectDB, Tables, get, getAll, isExists, insert, remove, removeList
from code.bot import mainBot

database = connectDB()
cursor = database.cursor()
allRows = getAll(cursor=cursor, table="FACULTS")
print(allRows)

database.commit()
database.close()