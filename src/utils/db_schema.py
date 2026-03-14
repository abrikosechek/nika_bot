"""
Схема базы данных для бота.
"""

# Список SQL-запросов для создания таблиц
SCHEMA = [
    # Приватные голосовые каналы
    """
    CREATE TABLE IF NOT EXISTS private_channels (
        channel_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        locked INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    # Индекс для поиска по пользователю и серверу
    """
    CREATE INDEX IF NOT EXISTS idx_private_channels_user 
    ON private_channels(user_id, guild_id)
    """,
    
    # Индекс для поиска по серверу
    """
    CREATE INDEX IF NOT EXISTS idx_private_channels_guild 
    ON private_channels(guild_id)
    """,
]
