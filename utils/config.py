import json
from pathlib import Path
from typing import Any


class ConfigManager:
    def __init__(self, guilds_path: Path, global_path: Path):
        self.guilds_path = Path(guilds_path)
        self.global_path = Path(global_path)
        self.guilds_data: dict[int, dict[str, Any]] = {}
        self.global_data: dict[str, Any] = {}
        self.load()

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Конфиг не найден: {path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Ошибка JSON в {path}: {e}")
            return {}
        except Exception as e:
            print(f"Ошибка загрузки {path}: {e}")
            return {}

        if not isinstance(data, dict):
            print(f"Некорректный формат конфига {path}: ожидается JSON object")
            return {}

        return data

    def load(self) -> None:
        raw_guilds_data = self._load_json(self.guilds_path)
        self.guilds_data.clear()

        for guild_id_str, guild_data in raw_guilds_data.items():
            try:
                guild_id_int = int(guild_id_str)
            except (TypeError, ValueError):
                print(f"Некорректный guild id в конфиге: {guild_id_str}")
                continue

            if isinstance(guild_data, dict):
                self.guilds_data[guild_id_int] = guild_data

        self.global_data = self._load_json(self.global_path)

    def get_guild(self, guild_id: int) -> dict[str, Any] | None:
        return self.guilds_data.get(guild_id)

    def get_category(self, guild_id: int, category: str) -> dict[str, Any] | None:
        guild_config = self.guilds_data.get(guild_id)
        if guild_config is None:
            return None

        category_config = guild_config.get(category)
        if not isinstance(category_config, dict):
            return None

        return category_config

    def get_global(self) -> dict[str, Any]:
        return self.global_data

    def get_god_user_id(self) -> int | None:
        raw = self.global_data.get("god_user_id")
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            print(f"Некорректный god_user_id в global config: {raw}")
            return None


current_dir = Path(__file__).resolve().parent
config_dir = current_dir.parent / "config"
guilds_config_path = config_dir / "guilds.json"
global_config_path = config_dir / "global.json"

config_manager = ConfigManager(guilds_config_path, global_config_path)
