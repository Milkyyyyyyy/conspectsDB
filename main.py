from code.database import databaseUtil
from code.database.repo import facultRepo
import sqlite3

database = sqlite3.connect(databaseUtil.CONSPECTS_DB)
cursor = database.cursor()
print(facultRepo.getAll(cursor=cursor))
database.commit()
database.close()