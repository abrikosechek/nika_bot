import random
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from src.core import Module
from src.utils.storage import get_fun_channel, get_bananza_not_allowed
from src.ui.bananza import (
    create_spin_embed,
    create_win_embed,
    create_lose_embed,
    SPIN_ANIMATION,
    SLOTS,
)


class RollModule(Module):
    """Модуль с развлекательными командами (бросок кубика)"""

    name = "fun"
    description = "Развлекательные команды"

    async def setup(self) -> None:
        """Регистрация команд модуля"""

        @self.bot.tree.command(name='roll', description='🎲 Бросает кубик (1-6)')
        @app_commands.describe(
            max='Максимальное число (по умолчанию 6, можно от 1 до 1000)'
        )
        async def roll(
            interaction: discord.Interaction,
            max: app_commands.Range[int, 1, 1000] = 6
        ):
            """Бросает кубик и возвращает случайное число от 1 до max"""
            guild_id = interaction.guild_id
            if not guild_id:
                await interaction.response.send_message(
                    'Эта команда работает только на серверах.',
                    ephemeral=True
                )
                return

            fun_channel_id = get_fun_channel(guild_id)
            if not fun_channel_id:
                await interaction.response.send_message(
                    'На этом сервере не настроен канал для развлечений.',
                    ephemeral=True
                )
                return

            if interaction.channel_id != fun_channel_id:
                await interaction.response.send_message(
                    f'Эта команда работает только в канале <#{fun_channel_id}>.',
                    ephemeral=True
                )
                return

            result = random.randint(1, max)
            await interaction.response.send_message(
                f'🎲 Выпало число: {result} (1-{max})'
            )

        @self.bot.tree.command(name='bananza', description='🎰 Испытай удачу в слот-машине!')
        async def bananza(interaction: discord.Interaction):
            """Слот-машина: 3 ячейки, если все совпали — победа!"""
            # Проверяем запрет
            banned_user = get_bananza_not_allowed()
            if banned_user and interaction.user.id == banned_user:
                await interaction.response.send_message(
                    '❌ Тимик иди работай',
                    ephemeral=False
                )
                return

            # Деферим ответ, чтобы получить возможность редактировать
            await interaction.response.defer()

            # Начальное сообщение с анимацией
            reels = ["🌀", "🌀", "🌀"]
            embed = create_spin_embed(reels, "🎰 Запуск...")
            message = await interaction.followup.send(embed=embed, wait=True)

            # Анимация вращения каждого барабана по очереди
            for i in range(3):
                # Вращаем все барабаны несколько раз
                for _ in range(4):
                    temp_reels = reels.copy()
                    temp_reels[i] = random.choice(SPIN_ANIMATION)
                    embed = create_spin_embed(temp_reels, "🎰 Вращение...")
                    await message.edit(embed=embed)
                    await asyncio.sleep(0.05)
                
                # Останавливаем текущий барабан
                reels[i] = random.choice(SLOTS)
                embed = create_spin_embed(reels, "🎰 Вращение...")
                await message.edit(embed=embed)
                await asyncio.sleep(0.1)

            # Финальный результат
            if reels[0] == reels[1] == reels[2]:
                embed = create_win_embed(reels)
            else:
                embed = create_lose_embed(reels)

            await message.edit(embed=embed)
