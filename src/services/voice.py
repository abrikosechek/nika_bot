"""
Voice сервис для управления голосовыми подключениями бота.

Предоставляет методы для подключения, отключения и перемещения
между голосовыми каналами с подробным логированием.
"""

import logging
from typing import Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Сервис для управления голосовыми подключениями.
    
    Пример использования:
        voice_service = VoiceService(bot)
        await voice_service.connect_to_channel(channel)
        await voice_service.disconnect()
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._current_channel: Optional[discord.VoiceChannel] = None
        self._voice_client: Optional[discord.VoiceClient] = None
    
    @property
    def current_channel(self) -> Optional[discord.VoiceChannel]:
        """Текущий голосовой канал, к которому подключён бот"""
        return self._current_channel
    
    @property
    def is_connected(self) -> bool:
        """Подключён ли бот к голосовому каналу"""
        return self._voice_client is not None and self._voice_client.is_connected()
    
    def _get_voice_client(self, guild: discord.Guild) -> Optional[discord.VoiceClient]:
        """Получить voice client для сервера"""
        return discord.utils.get(self.bot.voice_clients, guild=guild)
    
    async def connect_to_channel(
        self,
        channel: discord.VoiceChannel,
        *,
        timeout: float = 30.0,
        reconnect: bool = True
    ) -> bool:
        """
        Подключиться к голосовому каналу.
        
        Args:
            channel: Голосовой канал для подключения
            timeout: Таймаут подключения в секундах
            reconnect: Переподключаться ли при обрыве
            
        Returns:
            True если подключение успешно, False иначе
        """
        guild = channel.guild
        bot_member = guild.me
        
        if not bot_member:
            logger.error(f"❌ Не удалось получить участника бота на сервере {guild.name}")
            return False
        
        # Проверяем права бота
        if not channel.permissions_for(bot_member).connect:
            logger.error(f"❌ У бота нет права Connect в канале {channel.name}")
            return False
        
        try:
            logger.info(f"🔊 Подключение к каналу {channel.name} (ID: {channel.id}) на сервере {guild.name}")
            
            # Если уже подключены к этому каналу - ничего не делаем
            if self._current_channel and self._current_channel.id == channel.id:
                logger.debug(f"✅ Бот уже подключён к каналу {channel.name}")
                return True
            
            # Если подключены к другому каналу - сначала отключаемся
            if self.is_connected:
                logger.debug(f"🔌 Отключаемся от предыдущего канала")
                await self.disconnect()
            
            # Подключаемся к новому каналу
            self._voice_client = await channel.connect(timeout=timeout, reconnect=reconnect)
            self._current_channel = channel
            
            logger.info(f"✅ Успешно подключён к каналу {channel.name}")
            return True
            
        except discord.ClientException as e:
            logger.error(f"❌ Ошибка клиента при подключении: {e}")
            return False
        except discord.ConnectionClosed as e:
            logger.error(f"❌ Соединение закрыто: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при подключении: {e}", exc_info=True)
            return False
    
    async def disconnect(self) -> bool:
        """
        Отключиться от текущего голосового канала.
        
        Returns:
            True если отключение успешно, False если бот не был подключён
        """
        if not self.is_connected:
            logger.debug("ℹ️ Бот не подключён к голосовому каналу")
            return False
        
        try:
            old_channel = self._current_channel
            await self._voice_client.disconnect()
            
            self._voice_client = None
            self._current_channel = None
            
            if old_channel:
                logger.info(f"🔌 Отключён от канала {old_channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отключении: {e}")
            return False
    
    async def move_to_channel(
        self,
        channel: Optional[discord.VoiceChannel]
    ) -> bool:
        """
        Переместиться в другой голосовой канал (или отключиться).
        
        Args:
            channel: Канал для перемещения или None для отключения
            
        Returns:
            True если перемещение успешно, False иначе
        """
        if channel is None:
            return await self.disconnect()
        
        return await self.connect_to_channel(channel)
    
    def is_in_same_channel(self, member: discord.Member) -> bool:
        """
        Проверить, находится ли бот в том же канале, что и участник.
        
        Args:
            member: Участник для проверки
            
        Returns:
            True если бот и участник в одном канале
        """
        if not self.is_connected:
            return False
        
        if not member.voice or not member.voice.channel:
            return False
        
        return self._current_channel and self._current_channel.id == member.voice.channel.id
    
    async def follow_member(
        self,
        member: discord.Member
    ) -> bool:
        """
        Последовать за участником в его голосовой канал.
        
        Args:
            member: Участник, за которым следовать
            
        Returns:
            True если успешно последовали, False иначе
        """
        if not member.voice or not member.voice.channel:
            logger.debug(f"ℹ️ Участник {member.name} не в голосовом канале")
            return False
        
        # Если уже в том же канале - ничего не делаем
        if self.is_in_same_channel(member):
            logger.debug(f"✅ Бот уже в том же канале, что и {member.name}")
            return True
        
        # Подключаемся к каналу участника
        return await self.connect_to_channel(member.voice.channel)
