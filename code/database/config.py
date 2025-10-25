from enum import Enum

CONSPECTS_DB = 'files/database/conspects.db'


class Tables(str, Enum):
	FACULTS = 'facults'
	# wait_for_name - название факультета

	CHAIRS = 'chairs'
	# facult_id - rowid факультета из таблицы FACULTS
	# wait_for_name - имя кафедры

	DIRECTIONS = 'directions'
	# chair_id - rowid кафедры из таблицы CHAIRS
	# wait_for_name - имя направления

	SUBJECTS = 'subjects'
	# direction_id - rowid направления из таблицы DIRECTIONS
	# wait_for_name - имя предмета

	CONSPECTS = 'conspects'
	# subject_id - rowid из таблицы SUBJECTS
	# upload_date - дата публикации
	# conspect_date - дата написания конспекта (если не указывается, то равна upload_date)
	# user_telegram_id - telegram id пользователя, который загрузил
	# theme - тема конспекта (название)
	# keywords - теги/ключевые слова
	# views - кол-во просмотров
	# status - текущий статус конспекта ('pending' - в ожидании, 'accepted' - принят, 'rejected' - отклонён)
	# rating - текущий рейтинг (кол-во лайков минус кол-во дизлайков)
	# anonymous - запостили ли конспект анонимно

	CONSPECTS_FILES = 'conspects_files'
	# conspect_id - rowid конспекта, к которому относится файл
	# path - путь до файла

	USERS = 'users'
	# telegram_id - говорит само за себя
	# name - имя пользователя
	# surname - фамилия пользователя
	# study_group - группа, в которой он учится (возможно, не надо будет)
	# diredction_id - rowid из таблицы DIRECTIONS, в которой учится пользователь
	# role - роль пользователя ('user' или 'admin', возможно добавится отдельно 'moderator')
