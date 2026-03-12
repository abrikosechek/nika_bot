import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core import Module
from src.utils.storage import (
    get_private_category,
    get_private_voice_channel,
)

logger = logging.getLogger(__name__)

# Хранилище активных приватных каналов: {channel_id: {owner_id, owner, locked}}
_private_channels: dict[int, dict[str, int | discord.Member | bool]] = {}


class PrivateModule(Module):
    """
    Модуль приватных голосовых каналов.

    Логика:
    - Категория "Приватные" с текстовым каналом "шестерёнка управление"
      и голосовым "плюсик создать"
    - Пользователь заходит в "создать" → создаётся канал с его ником
    - Если все вышли → канал удаляется
    - У пользователя только один канал одновременно
    """

    name = "private_channels"
    description = "Система приватных голосовых каналов"

    async def setup(self) -> None:
        """Инициализация модуля"""

        @self.bot.tree.command(name='close', description='🚫 Закрыть свой приватный канал')
        async def close(interaction: discord.Interaction):
            """Закрыть свой приватный канал"""
            if not interaction.guild:
                await interaction.response.send_message(
                    'Эта команда работает только на серверах.',
                    ephemeral=True
                )
                return

            # Находим канал пользователя на этом сервере
            user_channel = self._get_user_channel(interaction.user.id, interaction.guild.id)

            if not user_channel:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            channel_data = _private_channels.get(user_channel.id)
            if not channel_data or channel_data.get('owner_id') != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Удаляем канал
            try:
                await user_channel.delete(reason='Закрыт владельцем')
                logger.info(f'🚫 Канал {user_channel.name} закрыт пользователем {interaction.user.name}')
                await interaction.response.send_message(
                    f'✅ Канал {user_channel.name} закрыт.',
                    ephemeral=True
                )
            except discord.Forbidden:
                logger.error(f'❌ Нет прав для удаления канала {user_channel.name}')
                await interaction.response.send_message(
                    '❌ Нет прав для удаления канала.',
                    ephemeral=True
                )
            except discord.HTTPException as e:
                logger.error(f'❌ Ошибка удаления канала: {e}')
                await interaction.response.send_message(
                    '❌ Ошибка при закрытии канала.',
                    ephemeral=True
                )

        @self.bot.tree.command(name='lock', description='🔒 Заблокировать вход в приватный канал')
        async def lock(interaction: discord.Interaction):
            """Заблокировать вход в приватный канал"""
            if not interaction.guild:
                await interaction.response.send_message(
                    'Эта команда работает только на серверах.',
                    ephemeral=True
                )
                return

            # Находим канал пользователя на этом сервере
            user_channel = self._get_user_channel(interaction.user.id, interaction.guild.id)

            if not user_channel:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            channel_data = _private_channels.get(user_channel.id)
            if not channel_data or channel_data.get('owner_id') != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Проверяем, не заблокирован ли уже
            if channel_data.get('locked', False):
                await interaction.response.send_message(
                    '🔒 Канал уже заблокирован.',
                    ephemeral=True
                )
                return

            # Блокируем канал
            try:
                # Запрещаем @everyone подключаться
                overwrite = user_channel.overwrites_for(interaction.guild.default_role)
                overwrite.connect = False
                await user_channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason='Канал заблоки владельцем'
                )

                # Обновляем хранилище
                _private_channels[user_channel.id]['locked'] = True

                # Меняем название канала
                old_name = user_channel.name
                if old_name.startswith('🔓 '):
                    new_name = old_name.replace('🔓 ', '🔒 ', 1)
                elif not old_name.startswith('🔒 '):
                    new_name = '🔒 ' + old_name[3:] if old_name.startswith('🔊 ') else '🔒 ' + old_name
                else:
                    new_name = old_name

                await user_channel.edit(name=new_name)

                logger.info(f'🔒 Канал {user_channel.name} заблокирован пользователем {interaction.user.name}')
                await interaction.response.send_message(
                    f'🔒 Канал заблокирован.',
                    ephemeral=True
                )
            except discord.Forbidden:
                logger.error(f'❌ Нет прав для изменения канала {user_channel.name}')
                await interaction.response.send_message(
                    '❌ Нет прав для блокировки канала.',
                    ephemeral=True
                )
            except discord.HTTPException as e:
                logger.error(f'❌ Ошибка блокировки канала: {e}')
                await interaction.response.send_message(
                    '❌ Ошибка при блокировке канала.',
                    ephemeral=True
                )

        @self.bot.tree.command(name='unlock', description='🔓 Разблокировать вход в приватный канал')
        async def unlock(interaction: discord.Interaction):
            """Разблокировать вход в приватный канал"""
            if not interaction.guild:
                await interaction.response.send_message(
                    'Эта команда работает только на серверах.',
                    ephemeral=True
                )
                return

            # Находим канал пользователя на этом сервере
            user_channel = self._get_user_channel(interaction.user.id, interaction.guild.id)

            if not user_channel:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            channel_data = _private_channels.get(user_channel.id)
            if not channel_data or channel_data.get('owner_id') != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Проверяем, не разблокирован ли уже
            if not channel_data.get('locked', False):
                await interaction.response.send_message(
                    '🔓 Канал уже разблокирован.',
                    ephemeral=True
                )
                return

            # Разблокируем канал
            try:
                # Разрешаем @everyone подключаться
                overwrite = user_channel.overwrites_for(interaction.guild.default_role)
                overwrite.connect = None  # Сбрасываем до значения по умолчанию
                await user_channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason='Канал разблокирован владельцем'
                )

                # Обновляем хранилище
                _private_channels[user_channel.id]['locked'] = False

                # Меняем название канала
                old_name = user_channel.name
                if old_name.startswith('🔒 '):
                    new_name = old_name.replace('🔒 ', '🔓 ', 1)
                elif not old_name.startswith('🔓 '):
                    new_name = '🔓 ' + old_name[3:] if old_name.startswith('🔊 ') else '🔓 ' + old_name
                else:
                    new_name = old_name

                await user_channel.edit(name=new_name)

                logger.info(f'🔓 Канал {user_channel.name} разблокирован пользователем {interaction.user.name}')
                await interaction.response.send_message(
                    f'🔓 Канал разблокирован.',
                    ephemeral=True
                )
            except discord.Forbidden:
                logger.error(f'❌ Нет прав для изменения канала {user_channel.name}')
                await interaction.response.send_message(
                    '❌ Нет прав для разблокировки канала.',
                    ephemeral=True
                )
            except discord.HTTPException as e:
                logger.error(f'❌ Ошибка разблокировки канала: {e}')
                await interaction.response.send_message(
                    '❌ Ошибка при разблокировке канала.',
                    ephemeral=True
                )

        logger.info('📁 PrivateModule: инициализирован')

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        """Обработка изменений голосового состояния"""
        guild_id = member.guild.id

        # Получаем каналы
        create_channel_id = get_private_voice_channel(guild_id)
        category_id = get_private_category(guild_id)

        if not create_channel_id or not category_id:
            return

        # Пользователь зашёл в канал создания
        if after.channel and after.channel.id == create_channel_id:
            await self._handle_join_create(member, guild_id, category_id)

        # Пользователь вышел из канала
        if before.channel and before.channel.id in _private_channels:
            await self._handle_leave_private(member, before.channel)

    async def _handle_join_create(
        self,
        member: discord.Member,
        guild_id: int,
        category_id: int
    ) -> None:
        """Обработка захода в канал создания"""
        # Проверяем, есть ли уже канал у пользователя на этом сервере
        existing_channel = self._get_user_channel(member.id, guild_id)

        if existing_channel:
            # Перемещаем в существующий канал
            try:
                await member.move_to(existing_channel)
                logger.debug(
                    f'🔁 {member.name} перемещён в свой канал {existing_channel.name}'
                )
            except discord.Forbidden:
                logger.warning(f'❌ Нет прав для перемещения {member.name}')
            except discord.HTTPException as e:
                logger.error(f'❌ Ошибка перемещения: {e}')
            return

        # Создаём новый канал
        category = member.guild.get_channel(category_id)
        if not category:
            logger.error(f'❌ Категория {category_id} не найдена')
            return

        try:
            # Создаём голосовой канал с именем пользователя
            new_channel = await member.guild.create_voice_channel(
                name=f"🔓 {member.display_name}",
                category=category,
                bitrate=64000,
                user_limit=20
            )

            # Добавляем в хранилище
            _private_channels[new_channel.id] = {
                'owner_id': member.id,
                'owner': member,
                'locked': False
            }

            # Перемещаем пользователя в новый канал
            await member.move_to(new_channel)
            logger.info(f'🎤 Создан приватный канал {new_channel.name} для {member.name}')

        except discord.Forbidden:
            logger.error(f'❌ Нет прав для создания канала')
            await member.move_to(None)  # Выкидываем из канала создания
        except discord.HTTPException as e:
            logger.error(f'❌ Ошибка создания канала: {e}')
            await member.move_to(None)

    async def _handle_leave_private(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel
    ) -> None:
        """Обработка выхода из приватного канала"""
        if channel.id not in _private_channels:
            return

        # Проверяем, остался ли кто-то в канале
        if len(channel.members) == 0:
            # Удаляем канал
            try:
                await channel.delete(reason='Приватный канал пуст')
                logger.info(f'🗑️ Удалён пустой приватный канал {channel.name}')
            except discord.Forbidden:
                logger.error(f'❌ Нет прав для удаления канала {channel.name}')
            except discord.HTTPException as e:
                logger.error(f'❌ Ошибка удаления канала: {e}')
            finally:
                # Удаляем из хранилища
                if channel.id in _private_channels:
                    del _private_channels[channel.id]

    def _get_user_channel(self, user_id: int, guild_id: int) -> discord.VoiceChannel | None:
        """Получить приватный канал пользователя на указанном сервере"""
        for channel_id, data in _private_channels.items():
            if data.get('owner_id') == user_id:
                # Находим канал в боте
                for guild in self.bot.guilds:
                    if guild.id != guild_id:
                        continue
                    channel = guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.VoiceChannel):
                        return channel
        return None

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Лог при входе на сервер"""
        logger.info(f'📁 PrivateModule добавлен на сервер {guild.name}')

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Очистка при выходе с сервера"""
        # Удаляем все каналы этого сервера из хранилища
        channels_to_remove = [
            ch_id for ch_id in list(_private_channels.keys())
            if self.bot.get_channel(ch_id) and
            self.bot.get_channel(ch_id).guild.id == guild.id
        ]
        for ch_id in channels_to_remove:
            del _private_channels[ch_id]
        logger.info(f'📁 PrivateModule удалён с сервера {guild.name}')
