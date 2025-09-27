from code.database.databaseProcessing import databaseUtil
import sqlite3

database = sqlite3.connect(databaseUtil.CONSPECTS_DB)
cursor = database.cursor()
# print(dbProcessing.getAll())
database.commit()
database.close()