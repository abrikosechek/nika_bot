from abc import ABC, abstractmethod
from typing import Optional

import discord
from discord.ext import commands


class Module(ABC):
    """
    Базовый класс для всех модулей бота.
    
    Каждый модуль должен реализовать:
    - name: имя модуля
    - description: описание модуля
    - setup(): метод регистрации команд и обработчиков
    """
    
    name: str
    description: str
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @abstractmethod
    async def setup(self) -> None:
        """
        Метод инициализации модуля.
        Здесь регистрируются команды, обработчики событий и т.д.
        """
        pass
    
    async def on_ready(self) -> None:
        """Вызывается когда бот готов (опционально)"""
        pass
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Вызывается при входе на новый сервер (опционально)"""
        pass
    
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Вызывается при выходе с сервера (опционально)"""
        pass
    
    async def on_member_join(self, member: discord.Member) -> None:
        """Вызывается при входе участника на сервер (опционально)"""
        pass
    
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Вызывается при добавлении реакции (опционально)"""
        pass
    
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        """Вызывается при изменении голосового состояния (опционально)"""
        pass
    
    def __repr__(self) -> str:
        return f"<Module(name={self.name!r}, description={self.description!r})>"
