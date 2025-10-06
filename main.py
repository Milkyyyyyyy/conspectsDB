from code.database.repo import facultRepo, chairRepo, directionRepo, subjectRepo
from code.database.repo.queries import connectDB

database = connectDB()
cursor = database.cursor()
print(subjectRepo.getAll(cursor=cursor))
# subjectRepo.removeList(cursor=cursor, idList=[4, 5, 6, 7, 8, 9, 10])
# subjectRepo.add(cursor=cursor, directionID=2, name="Нука")
# print(subjectRepo.getAll(cursor=cursor, value=1, valueName='direction_id'))
database.commit()
database.close()