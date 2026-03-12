import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.core import Module
from src.services.voice import VoiceService
from src.utils.storage import get_god_user, get_private_voice_channel

logger = logging.getLogger(__name__)


class GodModule(Module):
    """
    Модуль god mode - бот следует за god пользователем по голосовым каналам.

    Работает только для одного пользователя, указанного в поле _god в guilds.json.
    """

    name = "god"
    description = "Бот следует за god пользователем по голосовым каналам"

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.voice_service = VoiceService(bot)
        self._god_id: Optional[int] = None

    async def setup(self) -> None:
        """Инициализация модуля"""
        self._god_id = get_god_user()
        if self._god_id:
            logger.info(f"👻 God пользователь: {self._god_id}")
        else:
            logger.info("👻 God пользователь не установлен")

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        """Обработка изменения голосового состояния участника"""

        # Пропускаем ботов
        if member.bot:
            return

        # Проверяем god пользователя
        if self._god_id is None:
            return

        if member.id != self._god_id:
            return

        bot_member = member.guild.me
        if not bot_member:
            return

        # God покинул канал
        if after.channel is None and before.channel is not None:
            if self.voice_service.is_connected:
                current = self.voice_service.current_channel
                if current and current.id == before.channel.id:
                    await self.voice_service.disconnect()
            return

        # God перешёл в другой канал
        if after.channel is not None and before.channel != after.channel:
            # Не заходим в канал создания приватки
            private_create_id = get_private_voice_channel(member.guild.id)
            if private_create_id and after.channel.id == private_create_id:
                logger.debug(f"⏭️ Пропускаем канал создания приватки")
                return

            perms = after.channel.permissions_for(bot_member)
            if not perms.connect:
                return

            await self.voice_service.follow_member(member)
