"""
Модуль приватных голосовых каналов с хранением данных в SQLite.

Логика:
- Категория "Приватные" с текстовым каналом "шестерёнка управление"
  и голосовым "плюсик создать"
- Пользователь заходит в "создать" → создаётся канал с его ником
- Если все вышли → канал удаляется
- У пользователя только один канал одновременно
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core import Module
from src.utils.storage import (
    get_private_category,
    get_private_text_channel,
    get_private_voice_channel,
)
from src.utils.checks import check_allowed_channels
from src.utils.db import db
from src.utils.db_schema import SCHEMA

logger = logging.getLogger(__name__)


class PrivateModule(Module):
    """Модуль приватных голосовых каналов"""

    name = "private_channels"
    description = "Система приватных голосовых каналов"

    async def setup(self) -> None:
        """Инициализация модуля"""
        # Создаём таблицу в БД
        await db.create_tables(SCHEMA)
        logger.info('📁 PrivateModule: таблица БД создана')

        @self.bot.tree.command(name='close', description='🚫 Закрыть свой приватный канал')
        async def close(interaction: discord.Interaction):
            """Закрыть свой приватный канал"""
            if not interaction.guild:
                await interaction.response.send_message(
                    'Эта команда работает только на серверах.',
                    ephemeral=True
                )
                return

            # Проверяем, что команда вызвана в private_text канале
            private_text_id = get_private_text_channel(interaction.guild.id)
            if not private_text_id:
                await interaction.response.send_message(
                    '❌ На этом сервере не настроен канал управления.',
                    ephemeral=True
                )
                return

            await check_allowed_channels(interaction, private_text_id)

            # Находим канал пользователя в БД
            channel_data = await db.fetch_one(
                'SELECT channel_id, user_id, locked FROM private_channels WHERE user_id = ? AND guild_id = ?',
                (interaction.user.id, interaction.guild.id)
            )

            if not channel_data:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            if channel_data['user_id'] != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Получаем объект канала
            user_channel = interaction.guild.get_channel(channel_data['channel_id'])
            if not user_channel:
                await interaction.response.send_message(
                    '❌ Канал не найден.',
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

            # Проверяем, что команда вызвана в private_text канале
            private_text_id = get_private_text_channel(interaction.guild.id)
            if not private_text_id:
                await interaction.response.send_message(
                    '❌ На этом сервере не настроен канал управления.',
                    ephemeral=True
                )
                return

            await check_allowed_channels(interaction, private_text_id)

            # Находим канал пользователя в БД
            channel_data = await db.fetch_one(
                'SELECT channel_id, user_id, locked FROM private_channels WHERE user_id = ? AND guild_id = ?',
                (interaction.user.id, interaction.guild.id)
            )

            if not channel_data:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            if channel_data['user_id'] != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Проверяем, не заблокирован ли уже
            if channel_data['locked']:
                await interaction.response.send_message(
                    '🔒 Канал уже заблокирован.',
                    ephemeral=True
                )
                return

            # Получаем объект канала
            user_channel = interaction.guild.get_channel(channel_data['channel_id'])
            if not user_channel:
                await interaction.response.send_message(
                    '❌ Канал не найден.',
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

                # Обновляем БД
                await db.execute(
                    'UPDATE private_channels SET locked = 1 WHERE channel_id = ?',
                    (channel_data['channel_id'],)
                )

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

            # Проверяем, что команда вызвана в private_text канале
            private_text_id = get_private_text_channel(interaction.guild.id)
            if not private_text_id:
                await interaction.response.send_message(
                    '❌ На этом сервере не настроен канал управления.',
                    ephemeral=True
                )
                return

            await check_allowed_channels(interaction, private_text_id)

            # Находим канал пользователя в БД
            channel_data = await db.fetch_one(
                'SELECT channel_id, user_id, locked FROM private_channels WHERE user_id = ? AND guild_id = ?',
                (interaction.user.id, interaction.guild.id)
            )

            if not channel_data:
                await interaction.response.send_message(
                    '❌ У вас нет приватного канала.',
                    ephemeral=True
                )
                return

            # Проверяем, владелец ли
            if channel_data['user_id'] != interaction.user.id:
                await interaction.response.send_message(
                    '❌ Вы не владелец этого канала.',
                    ephemeral=True
                )
                return

            # Проверяем, не разблокирован ли уже
            if not channel_data['locked']:
                await interaction.response.send_message(
                    '🔓 Канал уже разблокирован.',
                    ephemeral=True
                )
                return

            # Получаем объект канала
            user_channel = interaction.guild.get_channel(channel_data['channel_id'])
            if not user_channel:
                await interaction.response.send_message(
                    '❌ Канал не найден.',
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

                # Обновляем БД
                await db.execute(
                    'UPDATE private_channels SET locked = 0 WHERE channel_id = ?',
                    (channel_data['channel_id'],)
                )

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

    async def on_ready(self) -> None:
        """Восстановление состояния приватных каналов после перезапуска"""
        # Загружаем все активные каналы из БД
        channels = await db.fetch_all('SELECT channel_id, user_id, guild_id, locked FROM private_channels')

        for channel_data in channels:
            channel_id = channel_data['channel_id']
            channel = self.bot.get_channel(channel_id)

            # Если канал больше не существует — удаляем из БД
            if not channel:
                await db.execute(
                    'DELETE FROM private_channels WHERE channel_id = ?',
                    (channel_id,)
                )
                continue

            # Проверяем, есть ли участники в канале
            if len(channel.members) == 0:
                # Пустой канал — удаляем из БД и Discord
                try:
                    await channel.delete(reason='Приватный канал пуст после перезапуска')
                    await db.execute(
                        'DELETE FROM private_channels WHERE channel_id = ?',
                        (channel_id,)
                    )
                    logger.info(f'🗑️ Удалён пустой канал {channel.name} после перезапуска')
                except discord.Forbidden:
                    logger.warning(f'⚠️ Нет прав для удаления канала {channel.name}')
                except discord.HTTPException as e:
                    logger.error(f'❌ Ошибка удаления канала: {e}')

        logger.info(f'🔄 PrivateModule: проверено {len(channels)} каналов после перезапуска')

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

        # Пользователь вышел из приватного канала
        if before.channel:
            await self._handle_leave_private(member, before.channel)

    async def _handle_join_create(
        self,
        member: discord.Member,
        guild_id: int,
        category_id: int
    ) -> None:
        """Обработка захода в канал создания"""
        # Проверяем, есть ли уже канал у пользователя в БД
        existing = await db.fetch_one(
            'SELECT channel_id FROM private_channels WHERE user_id = ? AND guild_id = ?',
            (member.id, guild_id)
        )

        if existing:
            # Проверяем, существует ли канал
            existing_channel = member.guild.get_channel(existing['channel_id'])
            if existing_channel:
                # Перемещаем в существующий канал
                try:
                    await member.move_to(existing_channel)
                    logger.debug(f'🔁 {member.name} перемещён в свой канал {existing_channel.name}')
                except discord.Forbidden:
                    logger.warning(f'❌ Нет прав для перемещения {member.name}')
                except discord.HTTPException as e:
                    logger.error(f'❌ Ошибка перемещения: {e}')
                return
            else:
                # Канал не найден — удаляем запись из БД
                await db.execute(
                    'DELETE FROM private_channels WHERE channel_id = ?',
                    (existing['channel_id'],)
                )

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

            # Сохраняем в БД
            await db.execute(
                'INSERT INTO private_channels (channel_id, user_id, guild_id, locked) VALUES (?, ?, ?, 0)',
                (new_channel.id, member.id, guild_id)
            )

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
        # Проверяем, приватный ли это канал
        channel_data = await db.fetch_one(
            'SELECT user_id FROM private_channels WHERE channel_id = ?',
            (channel.id,)
        )

        if not channel_data:
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
                # Удаляем из БД
                await db.execute(
                    'DELETE FROM private_channels WHERE channel_id = ?',
                    (channel.id,)
                )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Лог при входе на сервер"""
        logger.info(f'📁 PrivateModule добавлен на сервер {guild.name}')

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Очистка при выходе с сервера"""
        # Удаляем все каналы этого сервера из БД
        await db.execute(
            'DELETE FROM private_channels WHERE guild_id = ?',
            (guild.id,)
        )
        logger.info(f'📁 PrivateModule удалён с сервера {guild.name}')
