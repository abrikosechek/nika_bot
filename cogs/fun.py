import random
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from utils.decorators import check_guild_category
from utils.config import config_manager


class FunService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dice", description="roll  dice")
    @check_guild_category("fun")
    async def dice(self, interaction: discord.Interaction, max: int = 6):
        # check for text channel
        category_config = config_manager.get_category(interaction.guild_id, "fun")
        fun_text_channel = category_config.get("text_channel")
        if fun_text_channel is None:
            await interaction.response.send_message(
                "Текстовый канал для fun-категории не настроен", ephemeral=True
            )
            return
        if interaction.channel_id != fun_text_channel:
            await interaction.response.send_message(
                f"Эта команда работает только в <#{fun_text_channel}>", ephemeral=True
            )
            return

        # logic
        if max < 1 or max > 20:
            await interaction.response.send_message(
                "max может быть 1-20", ephemeral=True
            )
            return

        result = random.randint(1, max)

        await interaction.response.send_message("🎲 Кубик летит...")

        await asyncio.sleep(1)

        await interaction.edit_original_response(content=f"🎲 {result}")

    def _generateBananzaEmbed(
        self, state: str, slots: list = None, total_slots: int = 5
    ):
        state = state or "rolling"

        if slots is None:
            slots = []

        # дополняем до нужного количества элементов вопросами
        display_slots = slots + ["❓"] * (total_slots - len(slots))

        embedTitles = {
            "rolling": "🎰 в процессе...",
            "win": "🎰 джекпот",
            "lose": "🎰 минус хата",
        }

        embedColors = {
            "rolling": 0x25B9F5,
            "win": 0x25F586,
            "lose": 0xF5255C,
        }

        embedTitle = embedTitles.get(state, "🎰 Bananza")
        embedDescription = "|".join(display_slots)
        embedColor = embedColors.get(state, 0x25B9F5)

        embed = discord.Embed(
            title=embedTitle, description=embedDescription, color=embedColor
        )

        return embed

    @app_commands.command(name="bananza", description="gamble")
    @check_guild_category("fun")
    async def bananza(self, interaction: discord.Interaction, slots_count: int = 3):
        # check for text channel
        category_config = config_manager.get_category(interaction.guild_id, "fun")
        fun_text_channel = category_config.get("text_channel")
        if fun_text_channel is None:
            await interaction.response.send_message(
                "Текстовый канал для fun-категории не настроен", ephemeral=True
            )
            return
        if interaction.channel_id != fun_text_channel:
            await interaction.response.send_message(
                f"Эта команда работает только в <#{fun_text_channel}>", ephemeral=True
            )
            return

        # валидация количества барабанов
        if slots_count < 3 or slots_count > 12:
            await interaction.response.send_message(
                "Количество барабанов должно быть от 3 до 12", ephemeral=True
            )
            return

        # logic
        fruits = ["🍒", "🍋", "🍇", "🍉", "🍎"]

        # сразу подтверждаем команду, чтобы не было задержки отклика
        await interaction.response.defer()

        # начальные пустые барабаны
        slots = []
        embed = self._generateBananzaEmbed("rolling", slots, slots_count)
        await interaction.edit_original_response(
            content=f"Крутим барабаны... 0/{slots_count}", embed=embed
        )

        # поочерёдно открываем каждый барабан с короткой анимацией прокрутки
        for i in range(slots_count):
            preview_slots = slots.copy()

            # быстрые промежуточные кадры перед фиксацией результата
            for _ in range(3):
                rolling_preview = preview_slots + [random.choice(fruits)]
                embed = self._generateBananzaEmbed(
                    "rolling", rolling_preview, slots_count
                )
                await interaction.edit_original_response(
                    content=f"Крутим барабаны... {i}/{slots_count}",
                    embed=embed,
                )
                await asyncio.sleep(0.12)

            final_symbol = random.choice(fruits)
            slots.append(final_symbol)
            embed = self._generateBananzaEmbed("rolling", slots, slots_count)
            await interaction.edit_original_response(
                content=f"Крутим барабаны... {i + 1}/{slots_count}",
                embed=embed,
            )
            await asyncio.sleep(0.22)

        # проверяем, все ли фрукты совпадают
        if len(set(slots)) == 1:
            state = "win"
        else:
            state = "lose"

        result_text = (
            "💥 Джекпот! Все барабаны совпали."
            if state == "win"
            else "😢 Не повезло. Крутанем еще?"
        )

        embed = self._generateBananzaEmbed(state, slots, slots_count)
        await interaction.edit_original_response(content=result_text, embed=embed)


async def setup(bot):
    await bot.add_cog(FunService(bot))
