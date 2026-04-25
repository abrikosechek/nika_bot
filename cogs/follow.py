import discord
from discord.ext import commands
from utils.config import config_manager


class VoiceFollower(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_user_id = config_manager.get_god_user_id()
        self._voice_op_lock = None

    def _is_private_related_channel(self, guild_id: int, channel_id: int | None) -> bool:
        if channel_id is None:
            return False

        private_config = config_manager.get_category(guild_id, "private") or {}
        create_voice_channel = private_config.get("create_voice_channel")
        if channel_id == create_voice_channel:
            return True

        private_cog = self.bot.get_cog("PrivateRooms")
        if private_cog is None:
            return False

        return channel_id in private_cog.rooms_by_channel_id

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if self._voice_op_lock is None:
            import asyncio
            self._voice_op_lock = asyncio.Lock()

        if self.target_user_id is None:
            return

        if member.id != self.target_user_id:
            return

        if self._is_private_related_channel(member.guild.id, before.channel.id if before.channel else None):
            return
        if self._is_private_related_channel(member.guild.id, after.channel.id if after.channel else None):
            return

        if before.channel == after.channel:
            return

        async with self._voice_op_lock:
            bot_voice = member.guild.voice_client

            # user joined a channel
            if after.channel is not None:
                if bot_voice is None:
                    await after.channel.connect()
                else:
                    if bot_voice.channel is not None and bot_voice.channel.id == after.channel.id:
                        return
                    await bot_voice.move_to(after.channel)

            # user left voice
            elif after.channel is None:
                if bot_voice is not None:
                    await bot_voice.disconnect()


async def setup(bot):
    await bot.add_cog(VoiceFollower(bot))
