"""
Утилиты для работы с хранилищем данных.

Использует ConfigCache для кэширования данных в памяти.
"""

from typing import Any, Optional

from src.utils.config import config


def get_guild(guild_id: int) -> dict[str, Any]:
    """Получить данные сервера"""
    return config.get_guild(guild_id)


def set_guild(guild_id: int, data: dict[str, Any]) -> None:
    """Установить данные сервера"""
    config.set_guild(guild_id, data)


# ==================== VERIFICATION ====================

def get_unverif_role(guild_id: int) -> Optional[int]:
    """Получить ID роли unveref"""
    return config.get_nested(guild_id, 'verification', 'unverif_role')


def set_unverif_role(guild_id: int, role_id: int) -> None:
    """Установить ID роли unveref"""
    guild = get_guild(guild_id)
    guild.setdefault('verification', {})['unverif_role'] = role_id
    set_guild(guild_id, guild)


def get_verif_role(guild_id: int) -> Optional[int]:
    """Получить ID роли verif"""
    return config.get_nested(guild_id, 'verification', 'verif_role')


def set_verif_role(guild_id: int, role_id: int) -> None:
    """Установить ID роли verif"""
    guild = get_guild(guild_id)
    guild.setdefault('verification', {})['verif_role'] = role_id
    set_guild(guild_id, guild)


def get_react_verif_message(guild_id: int) -> Optional[int]:
    """Получить ID сообщения для верификации"""
    return config.get_nested(guild_id, 'verification', 'react_message_id')


def set_react_verif_message(guild_id: int, message_id: int) -> None:
    """Установить ID сообщения для верификации"""
    guild = get_guild(guild_id)
    guild.setdefault('verification', {})['react_message_id'] = message_id
    set_guild(guild_id, guild)


# ==================== FUN ====================

def get_fun_channel(guild_id: int) -> Optional[int]:
    """Получить ID канала для развлечений (fun)"""
    return config.get_nested(guild_id, 'fun', 'channel')


def set_fun_channel(guild_id: int, channel_id: int) -> None:
    """Установить ID канала для развлечений"""
    guild = get_guild(guild_id)
    guild.setdefault('fun', {})['channel'] = channel_id
    set_guild(guild_id, guild)


# ==================== PRIVATE CHANNELS ====================

def get_private_category(guild_id: int) -> Optional[int]:
    """Получить ID категории для приватных каналов"""
    return config.get_nested(guild_id, 'private_channels', 'category')


def set_private_category(guild_id: int, channel_id: int) -> None:
    """Установить ID категории для приватных каналов"""
    guild = get_guild(guild_id)
    guild.setdefault('private_channels', {})['category'] = channel_id
    set_guild(guild_id, guild)


def get_private_text_channel(guild_id: int) -> Optional[int]:
    """Получить ID текстового канала управления приватными каналами"""
    return config.get_nested(guild_id, 'private_channels', 'text_channel')


def set_private_text_channel(guild_id: int, channel_id: int) -> None:
    """Установить ID текстового канала управления приватными каналами"""
    guild = get_guild(guild_id)
    guild.setdefault('private_channels', {})['text_channel'] = channel_id
    set_guild(guild_id, guild)


def get_private_voice_channel(guild_id: int) -> Optional[int]:
    """Получить ID голосового канала для создания приватного канала"""
    return config.get_nested(guild_id, 'private_channels', 'voice_channel')


def set_private_voice_channel(guild_id: int, channel_id: int) -> None:
    """Установить ID голосового канала для создания приватного канала"""
    guild = get_guild(guild_id)
    guild.setdefault('private_channels', {})['voice_channel'] = channel_id
    set_guild(guild_id, guild)


# ==================== GOD MODE ====================

def get_god_user(guild_id: Optional[int] = None) -> Optional[int]:
    """
    Получить ID god пользователя.

    Args:
        guild_id: ID сервера (не используется, оставлен для совместимости)

    Returns:
        ID god пользователя или None
    """
    return config.get('_god')


def set_god_user_global(user_id: int) -> None:
    """Установить god пользователя (глобально)"""
    config.set('_god', user_id)


def remove_god_user_global() -> None:
    """Удалить god пользователя (глобально)"""
    config.set('_god', None)


# Для обратной совместимости
def set_god_user(guild_id: int, user_id: int) -> None:
    """Установить god пользователя (глобально)"""
    set_god_user_global(user_id)


def remove_god_user(guild_id: int) -> None:
    """Удалить god пользователя (глобально)"""
    remove_god_user_global()


# ==================== BANANZA ====================

def get_bananza_not_allowed() -> Optional[int]:
    """Получить ID пользователя, которому запрещено использовать bananza"""
    return config.get('bananza_not_allowed')


def set_bananza_not_allowed(user_id: int) -> None:
    """Установить пользователя, которому запрещено использовать bananza"""
    config.set('bananza_not_allowed', user_id)


def remove_bananza_not_allowed() -> None:
    """Убрать запрет на bananza"""
    config.set('bananza_not_allowed', None)
