import discord
from functools import wraps
from utils.config import config_manager


def check_guild_category(category: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx: discord.Interaction, *args, **kwargs):
            if not ctx.guild_id:
                await ctx.response.send_message(
                    "Эта команда работает только на серверах.", ephemeral=True
                )
                return

            guild_config = config_manager.get_guild(ctx.guild_id)
            if not guild_config:
                await ctx.response.send_message(
                    "Конфиг для этого сервера не настроен", ephemeral=True
                )
                return

            category_config = guild_config.get(category)
            if category_config is None:
                await ctx.response.send_message(
                    f"Конфиг для категории {category} не настроен", ephemeral=True
                )
                return

            return await func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator
