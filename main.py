from code.database import dbProcessing
import sqlite3

database = sqlite3.connect(dbProcessing.CONSPECTS_DB)
cursor = database.cursor()
print(dbProcessing.getAllSubjects(cursor=cursor))
print(dbProcessing.getSubjectObject(cursor=cursor, subjectID=1).getName())
database.commit()
database.close()