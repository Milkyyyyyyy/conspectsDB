from code.database.repo import facultRepo, chairRepo, directionRepo, subjectRepo
from code.database.repo.queries import connectDB

database = connectDB()
cursor = database.cursor()
print(subjectRepo.getAll(cursor=cursor))
obj = subjectRepo.getObject(cursor=cursor, subjectID=2)
print(f'Row ID = {obj.getID()}\nName = {obj.getName()}\nDirection ID = {obj.getDirectionID()}')
database.commit()
database.close()