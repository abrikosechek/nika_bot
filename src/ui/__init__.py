"""
UI компоненты для бота.

Модуль содержит функции для создания embed-сообщений,
кнопок, меню и других элементов интерфейса.
"""

from src.ui.bananza import (
    create_spin_embed,
    create_win_embed,
    create_lose_embed,
)

__all__ = [
    'create_spin_embed',
    'create_win_embed',
    'create_lose_embed',
]
