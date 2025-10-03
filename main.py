from code.database.repo import facultRepo
from code.database.repo.queries import connectDB

database = connectDB()
cursor = database.cursor()
print(facultRepo.getAll(cursor=cursor))
facultRepo.add(cursor=cursor, name="Тест новой архитектуры и логов")
database.commit()
database.close()