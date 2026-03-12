from abc import ABC, abstractmethod
from typing import Optional

import discord
from discord.ext import commands


class Service(ABC):
    """
    Базовый класс для сервисов бота.
    
    Сервисы — это переиспользуемые компоненты, которые не являются модулями.
    Они не регистрируют команды, а предоставляют функциональность для модулей.
    
    Примеры сервисов:
    - VoiceService: управление голосовыми подключениями
    - ConfigCache: кэширование конфигурации
    - DatabaseService: работа с базой данных
    """
    
    def __init__(self, bot: Optional[commands.Bot] = None):
        self.bot = bot
    
    @abstractmethod
    async def start(self) -> None:
        """
        Инициализация сервиса.
        
        Вызывается при старте бота после загрузки всех модулей.
        Здесь можно запустить фоновые задачи, подключиться к БД и т.д.
        """
        pass
    
    async def stop(self) -> None:
        """
        Остановка сервиса.
        
        Вызывается при остановке бота.
        Здесь нужно освободить ресурсы: закрыть соединения, остановить задачи.
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
