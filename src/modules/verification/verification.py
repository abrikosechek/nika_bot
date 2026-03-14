import discord
from discord.ext import commands

from src.core import Module
from src.utils.storage import (
    get_unverif_role,
    get_verif_role,
    get_react_verif_message,
)


class VerificationModule(Module):
    """Модуль верификации участников через реакцию"""

    name = "verification"
    description = "Система верификации участников"

    async def setup(self) -> None:
        """Инициализация модуля верификации"""
        pass

    async def on_member_join(self, member: discord.Member) -> None:
        """Автовыдача unverif роли новому участнику"""
        guild_id = member.guild.id
        role_id = get_unverif_role(guild_id)

        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                print(f'Выдана unveref роль пользователю {member.name} на сервере {member.guild.name}')

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Обработка добавления реакции для верификации"""
        guild_id = payload.guild_id
        message_id = payload.message_id
        user_id = payload.user_id

        # Проверяем, то ли это сообщение для верификации
        verif_message_id = get_react_verif_message(guild_id)
        if message_id != verif_message_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(user_id)
        if not member:
            return

        # Получаем роли
        unverif_role_id = get_unverif_role(guild_id)
        verif_role_id = get_verif_role(guild_id)

        if not unverif_role_id or not verif_role_id:
            return

        unverif_role = guild.get_role(unverif_role_id)
        verif_role = guild.get_role(verif_role_id)

        if unverif_role and verif_role:
            # Забираем unverif, выдаём verif
            if unverif_role in member.roles:
                await member.remove_roles(unverif_role, reason='Верификация')
                await member.add_roles(verif_role, reason='Верификация')
                
                # Удаляем реакцию пользователя с сообщения
                channel = guild.get_channel(payload.channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.remove_reaction(payload.emoji, member)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass  # Не удалось удалить реакцию
                
                print(f'Пользователь {member.name} прошёл верификацию')

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Обработка снятия реакции для верификации"""
        guild_id = payload.guild_id
        message_id = payload.message_id
        user_id = payload.user_id

        # Проверяем, то ли это сообщение для верификации
        verif_message_id = get_react_verif_message(guild_id)
        if message_id != verif_message_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(user_id)
        if not member:
            return

        # Просто удаляем реакцию, роли не меняем
        # Пользователь может добавить её снова если хочет
        print(f'Пользователь {member.name} снял реакцию с сообщения верификации')
