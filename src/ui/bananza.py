"""
UI компоненты для слот-машины (Bananza).
"""

import discord

# Символы для слот-машины
SLOTS = ["🍒", "🍋", "7️⃣"]

# Анимация вращения для каждого барабана
SPIN_ANIMATION = ["🌀", "🍒", "🍋", "7️⃣"]


def create_spin_embed(reels: list[str], title: str = "🎰 Bananza!") -> discord.Embed:
    """
    Создаёт embed для вращающейся слот-машины.
    
    Args:
        reels: Список из 3 символов для барабанов
        title: Заголовок embed
    
    Returns:
        discord.Embed с золотым цветом
    """
    embed = discord.Embed(
        title=title,
        description=f"┃ {reels[0]} ┃ {reels[1]} ┃ {reels[2]} ┃",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Испытай удачу!")
    return embed


def create_win_embed(reels: list[str]) -> discord.Embed:
    """
    Создаёт embed для победы.
    
    Args:
        reels: Список из 3 символов для барабанов
    
    Returns:
        discord.Embed с зелёным цветом и сообщением о победе
    """
    embed = discord.Embed(
        title="🎉 УРА, ПОБЕДА! 🎉",
        description=f"┃ {reels[0]} ┃ {reels[1]} ┃ {reels[2]} ┃",
        color=discord.Color.green()
    )
    embed.add_field(name="🏆 Выигрыш!", value="Все символы совпали!", inline=False)
    embed.set_footer(text="✨ Отличный результат!")
    return embed


def create_lose_embed(reels: list[str]) -> discord.Embed:
    """
    Создаёт embed для проигрыша.
    
    Args:
        reels: Список из 3 символов для барабанов
    
    Returns:
        discord.Embed с красным цветом и сообщением о проигрыше
    """
    embed = discord.Embed(
        title="😢 Перемоги не будэ",
        description=f"┃ {reels[0]} ┃ {reels[1]} ┃ {reels[2]} ┃",
        color=discord.Color.red()
    )
    embed.add_field(name="Не повезло!", value="Попробуй ещё раз!", inline=False)
    embed.set_footer(text="🍀 Удача обязательно придёт!")
    return embed
