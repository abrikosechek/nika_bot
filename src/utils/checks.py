"""
Проверки (checks) для команд бота.

Предоставляет декораторы для ограничения доступа к командам
на основе каналов, ролей и других условий.
"""

from functools import wraps
from typing import Callable

import discord
from discord import app_commands


class ChannelCheckError(app_commands.AppCommandError):
    """Исключение, вызываемое при неудачной проверке канала"""

    def __init__(self, channel_ids: list[int]):
        self.channel_ids = channel_ids
        channels_mention = ", ".join(f"<#{ch_id}>" for ch_id in channel_ids)
        self.message = f"Эта команда доступна только в {channels_mention}"
        super().__init__(self.message)


def allowed_channels(*channel_ids: int):
    """
    Декоратор для ограничения команды определёнными каналами.

    Args:
        *channel_ids: ID каналов, в которых разрешено использование команды

    Raises:
        ChannelCheckError: Если команда вызвана вне разрешённых каналов

    Пример:
        @allowed_channels(123456789, 987654321)
        async def my_command(interaction: discord.Interaction):
            ...
    """
    if not channel_ids:
        raise ValueError("Должен быть указан хотя бы один канал")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if interaction.channel_id not in channel_ids:
                raise ChannelCheckError(list(channel_ids))
            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator


async def check_allowed_channels(
    interaction: discord.Interaction,
    *channel_ids: int
) -> None:
    """
    Асинхронная проверка каналов (для использования внутри команд).

    Args:
        interaction: Взаимодействие для проверки
        *channel_ids: ID разрешённых каналов

    Raises:
        ChannelCheckError: Если команда вызвана вне разрешённых каналов

    Пример:
        async def my_command(interaction: discord.Interaction):
            await check_allowed_channels(interaction, channel_id_1, channel_id_2)
            # Дальнейшая логика команды
    """
    if not channel_ids:
        raise ValueError("Должен быть указан хотя бы один канал")

    if interaction.channel_id not in channel_ids:
        raise ChannelCheckError(list(channel_ids))
