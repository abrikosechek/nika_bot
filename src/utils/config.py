"""
Модуль кэширования конфигурации.

Кэширует данные из guilds.json в памяти для улучшения производительности.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

DATA_FILE = 'config/guilds.json'  # По умолчанию
TEST_DATA_FILE = 'config/test_guilds.json'


def _get_data_file() -> str:
    """Получить путь к файлу данных в зависимости от IS_TEST"""
    is_test = os.getenv('IS_TEST', 'false').lower() == 'true'
    return TEST_DATA_FILE if is_test else DATA_FILE


class ConfigCache:
    """
    Кэш конфигурации бота.

    Загружает guilds.json (или test_guilds.json) один раз при старте
    и хранит в памяти. При необходимости можно перезагрузить через reload().
    
    Если IS_TEST=true в .env, используется data/test_guilds.json
    """
    
    def __init__(self):
        self._data: dict[str, Any] = {}
        self._loaded = False
    
    def reload(self) -> None:
        """Перезагрузить данные из файла"""
        path = Path(_get_data_file())
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {}
        self._loaded = True
    
    def _ensure_loaded(self) -> None:
        """Убедиться, что данные загружены"""
        if not self._loaded:
            self.reload()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу"""
        self._ensure_loaded()
        return self._data.get(key, default)
    
    def get_guild(self, guild_id: int) -> dict[str, Any]:
        """Получить данные сервера"""
        self._ensure_loaded()
        return self._data.get(str(guild_id), {})
    
    def get_nested(
        self,
        guild_id: Optional[int],
        *keys: str,
        default: Any = None
    ) -> Any:
        """
        Получить вложенное значение.
        
        Args:
            guild_id: ID сервера или None для глобальных настроек
            *keys: Ключи для вложенного доступа
            default: Значение по умолчанию
        
        Пример:
            config.get_nested(guild_id, 'channels', 'fun_channel')
        """
        self._ensure_loaded()
        
        if guild_id is not None:
            data = self._data.get(str(guild_id), {})
        else:
            data = self._data
        
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return default
        
        return data if data is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """Установить значение по ключу"""
        self._ensure_loaded()
        self._data[key] = value
        self._save()
    
    def set_guild(self, guild_id: int, data: dict[str, Any]) -> None:
        """Установить данные сервера"""
        self._ensure_loaded()
        self._data[str(guild_id)] = data
        self._save()
    
    def _save(self) -> None:
        """Сохранить данные в файл"""
        path = Path(_get_data_file())
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


# Глобальный экземпляр кэша
config = ConfigCache()


def is_test_mode() -> bool:
    """Проверить, включён ли тестовый режим"""
    return os.getenv('IS_TEST', 'false').lower() == 'true'
