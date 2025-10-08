from enum import Enum
import re
from code.logging import logger
import sqlite3
import functools
from typing import Union, Dict, Any, Optional, Iterable, Tuple


# ========== Константы ==========
CONSPECTS_DB = 'files/database/conspects.db'
class Tables(str, Enum):
    CHAIRS          = 'chairs'
    CONSPECTS       = 'conspects'
    CONSPECTS_FILES = 'conspects_files'
    DIRECTIONS      = 'directions'
    FACULTS         = 'facults'
    SUBJECTS        = 'subjects'
    USERS           = 'users'
    # Добавлять новые таблицы сюда

# Проверка идентификатора
_SIMPLE_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


# ======================================

def connectDB() -> Optional[sqlite3.Connection]:
    """
    Возвращает датабазу conspects.db
    :return: sqlite3.Connection
    """
    logger.info('Connecting to database...')
    try:
        output = sqlite3.connect(CONSPECTS_DB)
        logger.info('Successfully connected to database.')
        return output
    except sqlite3.Error as e:
        logger.error(e)
        return None
def checkCursor(cursor: Union[sqlite3.Cursor] = None) -> bool:
    """
    Возвращает True, если cursor валидный
    :param cursor: sqlite3.Cursor --> курсор подключения к датабазе
    :return: bool
    """
    if isinstance(cursor, sqlite3.Cursor):
        return True
    return False
def checkDatabase(database:sqlite3.Connection) -> bool:
    return isinstance(database, sqlite3.Connection)
def require_cursor(func):
    """
    Проверка наличия курсора
    """
    @functools.wraps(func)
    def wrapper(cursor, *args, **kwargs):
        if not checkCursor(cursor):
            Exception("Invalid cursor")
        return func(cursor, *args, **kwargs)
    return wrapper

def _safe_identifier(name: str, allow_quoted: bool = True) -> str:
    """
    Возвращает безопасную строку для подстановки
    в SQL запрос
    """
    if not isinstance(name, str):
        raise ValueError("Identifier must be a string")

    if _SIMPLE_IDENT_RE.match(name):
        return name

    if allow_quoted:
        if "\x00" in name:
            raise ValueError("Invalid identifier (null byte)")
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    raise ValueError(f"Invalid SQL identifier: {name!r}")

def _resolve_table(table: Union[str, Enum]) -> str:
    """
    Возвращает название таблицы из enum Tables
    """
    if table is None:
        raise ValueError("Table must be provided")

    # Если передан Enum: используем его value
    if isinstance(table, Enum):
        table_name = table.value
    else:
        table_name = str(table)
    return _safe_identifier(table_name)

def _validate_identifier(name: str = None):
    if not isinstance(name, str) or not _SIMPLE_IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name

def _build_where_clause(filters, operator="AND"):
    if not filters:
        return "", ()

    if operator not in ("AND", "OR"):
        operator = "AND"

    parts = []
    params = []
    for col, val in filters.items():
        _validate_identifier(col)
        if val is None:
            parts.append(f"{col} IS NULL")
        elif isinstance(val, (list, tuple)):
            if len(val) == 0:
                parts.append("0")
            else:
                placeholders = ", ".join("?" for _ in val)
                parts.append(f"{col} IN ({placeholders})")
                params.extend(val)
        else:
            parts.append(f"{col} = ?")
            params.append(val)

    where_sql = " WHERE " + f" {operator} ".join(parts)
    return where_sql, tuple(params)

def getAll(
        database:sqlite3.Connection = None,
        table: Union[str, Enum] = None,
        filters: Dict[str, Any] = None,
        operator: str = "AND") -> Union[Tuple[list, sqlite3.Cursor], None]:
    """
    Возвращает все записи из таблицы, которые соответствуют заданным фильтрам

    :param database: sqlite3.Connection --> Датабаза
    :param table:    str, Enum          --> Название таблицы из Tables
    :param filters:  dict, str          --> Фильтры
    :param operator: str                --> Оператор фильтра, "AND" или "OR"

    :return: list --> список всех найденных записей

    Пример использования
    input: getAll(cursor=cursor, table="USERS", filters = {"direction_id: "2"})
    output: список всех пользователей с ID направлением, равный 2
    """
    # Проверка датабазы
    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return None

    # Инициализируем курсор


    # Проверяем существует ли таблица с заданными фильтрами
    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return None

    logger.info(f'Getting rows from "{table_sql}" with filters={filters}...')

    # Собираем запрос SQL и возвращаем ответ
    try:
        where_sql, params = _build_where_clause(filters or {}, operator)
        sql_query = f"SELECT rowid, * FROM {table_sql}{where_sql}"
        logger.debug("SQL: %s -- params=%s", sql_query, params)
        cursor.execute(sql_query, params)
        output = cursor.fetchall()
        logger.info("Successfully fetched rows")
        return output, cursor
    except Exception as e:
        logger.exception(e)
        return None
def get(
        database:sqlite3.Connection = None,
        table: Union[str, Enum] = None,
        filters: Dict[str, Any] = None,
        operator: str = "AND") -> Union[Tuple[tuple, sqlite3.Cursor], None]:
    """
    Возвращает первую строку из таблицы, соответствующую заданным фильтрам
    Если фильтр пустой, то вернёт первую строку таблицы
    :param database: sqlite3.Connection --> Датабаза
    :param table:    enum, str          --> Название таблицы из Tables
    :param filters:  dict               --> Фильтры поиска
    :param operator: str                --> Оператор фильтра, "AND" или "OR"

    :return: Кортеж строки; курсор (нужен для получения названий полей)

    Пример использования
    input: get(cursor=cursor, table="FACULTS", filters={"name": "<NAME>"})
    output: Первая запись с заданным именем
    """
    # Проверка датабазы
    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return None

    # Разрешаем Enum или str --> название таблицы
    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return None

    logger.info(f'Getting single row from "{table_sql}" with filters={filters}...')

    # Собираем запрос SQL
    try:
        where_sql, params = _build_where_clause(filters or {}, operator=operator)
        sql_query = f"SELECT rowid, * FROM {table_sql} {where_sql}"
        logger.debug("SQL: %s -- params=%s", sql_query, params)
        cursor.execute(sql_query, params)
        output = cursor.fetchone()
        logger.info("Successfully fetched row")
        return output, cursor
    except Exception as e:
        logger.exception(e)
        return None
def isExists(
        database:sqlite3.Connection = None,
        table:Union[str, Enum] = None,
        filters:Dict[str, Any] = None,
        operator: str = 'AND') -> Union[bool, Tuple[bool, sqlite3.Cursor], None]:
    """
    Возвращает True, если запись, соответствующая заданным фильтрам, существует
    Если вводные данные ошибочны, возвращает None

    :param database: sqlite3.Connection  --> Датабаза
    :param table:    enum, str           --> Название таблицы из Tables
    :param filters:  dict                --> Фильтры поиска
    :param operator: str, None           --> Оператор фильтра, "AND" или "OR"

    :return: True или False; курсор (нужен для получения названий полей)

    Пример использования
    input: isExists(cursor=cursor, table="USERS", filters={"telegram_id": "abcdef"})
    output: True, если пользователь
    """
    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return None

    logger.info(f'Check if "{table}" entry exists with filters={filters}...')

    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return None

    if not filters or not isinstance(filters, dict):
        logger.error("Invalid filter argument")
        return False

    try:
        where_sql, params = _build_where_clause(filters, operator)

        sql_query = f'SELECT 1 FROM {table_sql}{where_sql} LIMIT 1'
        logger.debug("SQL: %s -- params=%s", sql_query, params)
        cursor.execute(sql_query, params)
        output = cursor.fetchone()
        exists = output is not None
        if exists:
            logger.info("Matching row exists")
        else:
            logger.info("No matching rows found")
        return exists, cursor
    except Exception as e:
        logger.exception(e)
        return None
def remove(
        database:sqlite3.Connection = None,
        table:Union[str, Enum] = None,
        filters:Dict[str, Any] = None,
        operator: str = "AND") -> Union[bool, Tuple[bool, sqlite3.Cursor], None]:
    """
    Удаляет запись в датабазе, соответствующую заданным фильтрам

    :param database: sqlite3.Connection  --> Датабаза
    :param table:    enum, str           --> Название таблицы из Tables
    :param filters:  dict                --> Фильтры поиска
    :param operator: str, None           --> Оператор фильтра, "AND" или "OR"

    :return: Было ли произведено удаление; курсор (нужен для получения названий полей)
    """
    logger.info(f'Removing row from "{table}" with filters={filters}...')

    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return None

    if not filters or not isinstance(filters, dict):
        logger.error("Invalid filter argument")
        return False

    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return False

    try:
        where_sql, params = _build_where_clause(filters, operator)
    except Exception:
        logger.exception("Invalid filter argument")
        return False

    try:
        select_sql = f"SELECT rowid from {table_sql} {where_sql} LIMIT 1"
        logger.debug("SQL (select rowid): %s -- params=%s", select_sql, params)
        cursor.execute(select_sql, params)
        row = cursor.fetchone()
        if row is None:
            logger.error("No matching rows found")
            return False
        rowid = row[0]
        logger.debug(f"SQL: selected rowid = {rowid}")
    except Exception as e:
        logger.exception(e)
        return False

    try:
        delete_sql = f"DELETE FROM {table_sql} WHERE rowid = ?"
        logger.debug("SQL (delete): %s -- params=%s", delete_sql, (rowid, ))
        cursor.execute(delete_sql, (rowid,))
        logger.info("Successfully deleted row")
        return True
    except Exception as e:
        logger.exception(e)
        return False
def removeList(
        database:sqlite3.Connection = None,
        table:Union[str, Enum] = None,
        rowids: Iterable = None) -> Union[int, Tuple[int, sqlite3.Cursor], None]:
    """
    Удаляет множество записей из датабазы

    :param database: sqlite3.Connection  --> Датабаза
    :param table:  enum, str             --> Название таблицы из Tables
    :param rowids: Iterable              --> Список всех rowid

    :return: Кол-во удалённых записей; None; курсор (нужен для получения названий полей)
    """

    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return None

    logger.info(f'Removing rows from "{table}": rowids={rowids}...')

    if rowids is None:
        logger.error("rowids list must be provided")
        return None

    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return None

    try:
        rowid_list = []
        for r in rowids:
            if isinstance(r, int):
                rowid_list.append(r)
            else:
                rowid_list.append(int(r))
    except Exception:
        logger.exception("Invalid rowid in rowids; all rowids must be INTEGER")
        return None

    if len(rowid_list) == 0:
        logger.info("Empty rowid list; nothing to delete")
        return 0

    try:
        placeholders = ", ".join("?" for _ in rowid_list)
        delete_sql = f"DELETE FROM {table_sql} WHERE rowid IN ({placeholders})"
        logger.debug("SQL (bulk delete): %s -- params=%s", delete_sql, rowid_list)
        cursor.execute(delete_sql, tuple(rowid_list))
        deleted = cursor.rowcount if isinstance(cursor.rowcount, int) and cursor.rowcount >= 0 else None
        if deleted is None:
            deleted = len(rowid_list)
        logger.info("Deleted %d rows (requested %d)",  deleted, len(rowid_list))
        return deleted, cursor
    except Exception as e:
        logger.exception(e)
        return None
def insert(
        database:sqlite3.Connection = None,
        table:Union[str, Enum] = None,
        values:Iterable = None,
        columns:Iterable = None) -> Union[bool, Tuple[bool, sqlite3.Cursor], Tuple[int, sqlite3.Cursor]]:
    """
    :param database: sqlite3.Connection  --> Датабаза
    :param table:   enum, str            --> Название таблицы из Tables
    :param values:  Iterable             --> Список значений
    :param columns: Iterable             --> Список полей

    :return: Истинность добавления; последний rowid, если доступен; курсор (нужен для получения названий полей)
    """

    try:
        cursor = database.cursor()
    except Exception:
        logger.error("Invalid database connection")
        return False

    logger.info(f'Inserting into "{table}": values={values}, columns={columns}')

    if values is None:
        logger.error("Values must be provided")
        return False
    vals = tuple()
    try:
        vals = tuple(values)
    except Exception:
        logger.exception("Values must be an iterable")

    if len(vals) == 0:
        logger.error("Values must contain at least one value")
        return False

    try:
        table_sql = _resolve_table(table)
    except Exception:
        logger.exception("Invalid table argument")
        return False

    columns_sql = ""
    if columns is not None:
        try:
            cols = list(columns)
        except Exception:
            logger.exception("Columns must be an iterable of strings")
            return False

        if len(cols) != len(vals):
            logger.error(f'Number of columns ({len(cols)}) does not match number of values ({len(vals)})')
            return False

        try:
            safe_cols = ", ".join(_safe_identifier(c) for c in cols)
            columns_sql = f"({safe_cols})"
        except Exception:
            logger.exception("Invalid column name in columns")
            return False

        try:
            placeholders = ", ".join("?" for _ in vals)
            sql_query = f'INSERT INTO {table_sql} {columns_sql} VALUES ({placeholders})'
            logger.debug("SQL (insert): %s -- params=%s", sql_query, values)
            cursor.execute(sql_query, values)

            last_id = getattr(cursor, "lastrowid", None)
            if isinstance(last_id, int) and last_id > 0:
                logger.info("Insert successful, lastrowid = %s", last_id)
                return last_id, cursor
            else:
                logger.info("Insert successful (lastrowid not available, return True")
                return True, cursor
        except Exception as e:
            logger.exception(e)
            return False