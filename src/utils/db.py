"""
Модуль для работы с SQLite базой данных.

Предоставляет асинхронный интерфейс для подключения,
чтения, записи и управления базой данных.
"""

import aiosqlite
from pathlib import Path

# Путь к базе данных
DB_PATH = Path("db/bot.db")


class Database:
    """
    Асинхронный клиент для SQLite базы данных.
    
    Пример использования:
        db = Database()
        await db.connect()
        
        # Чтение
        results = await db.fetch_all("SELECT * FROM users")
        
        # Запись
        await db.execute(
            "INSERT INTO users (name) VALUES (?)",
            ("Alice",)
        )
        
        await db.close()
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    @property
    def is_connected(self) -> bool:
        """Проверка подключения к базе данных"""
        return self._connection is not None

    async def connect(self) -> None:
        """
        Подключение к базе данных.
        
        Создаёт директорию для БД если она не существует.
        """
        # Создаём директорию если не существует
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Подключаемся к базе
        self._connection = await aiosqlite.connect(self.db_path)
        
        # Включаем режим WAL для лучшей производительности
        await self._connection.execute("PRAGMA journal_mode=WAL")
        
        # Включаем внешние ключи
        await self._connection.execute("PRAGMA foreign_keys=ON")

    async def close(self) -> None:
        """Закрытие подключения к базе данных"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def execute(self, query: str, parameters: tuple = ()) -> None:
        """
        Выполнение SQL-запроса без возврата результатов.
        
        Args:
            query: SQL-запрос
            parameters: Параметры для запроса
        """
        if not self.is_connected:
            await self.connect()
        
        async with self._connection.execute(query, parameters) as cursor:
            await self._connection.commit()

    async def fetch_one(self, query: str, parameters: tuple = ()) -> dict | None:
        """
        Получение одной строки из базы данных.
        
        Args:
            query: SQL-запрос
            parameters: Параметры для запроса
            
        Returns:
            Словарь с данными или None если ничего не найдено
        """
        if not self.is_connected:
            await self.connect()
        
        self._connection.row_factory = aiosqlite.Row
        async with self._connection.execute(query, parameters) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, parameters: tuple = ()) -> list[dict]:
        """
        Получение всех строк из базы данных.
        
        Args:
            query: SQL-запрос
            parameters: Параметры для запроса
            
        Returns:
            Список словарей с данными
        """
        if not self.is_connected:
            await self.connect()
        
        self._connection.row_factory = aiosqlite.Row
        async with self._connection.execute(query, parameters) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def fetch_val(self, query: str, parameters: tuple = (), column: int = 0) -> any:
        """
        Получение одного значения из базы данных.
        
        Args:
            query: SQL-запрос
            parameters: Параметры для запроса
            column: Индекс колонки для возврата
            
        Returns:
            Значение или None если ничего не найдено
        """
        if not self.is_connected:
            await self.connect()
        
        async with self._connection.execute(query, parameters) as cursor:
            row = await cursor.fetchone()
            return row[column] if row else None

    async def executemany(self, query: str, parameters_list: list[tuple]) -> None:
        """
        Выполнение SQL-запроса для нескольких наборов параметров.
        
        Args:
            query: SQL-запрос
            parameters_list: Список кортежей с параметрами
        """
        if not self.is_connected:
            await self.connect()
        
        await self._connection.executemany(query, parameters_list)
        await self._connection.commit()

    async def create_tables(self, schema: str | list[str]) -> None:
        """
        Создание таблиц по схеме.
        
        Args:
            schema: SQL-схема (строка или список строк) для создания таблиц
        """
        if isinstance(schema, list):
            for statement in schema:
                await self.execute(statement)
        else:
            await self.execute(schema)


# Глобальный экземпляр базы данных
db = Database()
