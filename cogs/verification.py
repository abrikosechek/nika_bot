import discord
from discord.ext import commands
from utils.config import config_manager


class VerificationService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _as_int(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_verification_config(self, guild_id: int) -> dict:
        category = config_manager.get_category(guild_id, "verification")
        if isinstance(category, dict):
            return category
        return {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        verification_config = self._get_verification_config(member.guild.id)
        unverified_role_id = self._as_int(verification_config.get("unverified_role_id"))
        if unverified_role_id is None:
            return

        unverified_role = member.guild.get_role(unverified_role_id)
        if unverified_role is None:
            return

        try:
            await member.add_roles(unverified_role, reason="Initial unverified role on join")
        except (discord.Forbidden, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        user_id = payload.user_id
        if user_id == self.bot.user.id if self.bot.user else False:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        verification_config = self._get_verification_config(guild.id)
        message_id = self._as_int(verification_config.get("message_id"))
        verified_role_id = self._as_int(verification_config.get("verified_role_id"))
        unverified_role_id = self._as_int(verification_config.get("unverified_role_id"))

        if message_id is None or verified_role_id is None:
            return

        if payload.message_id != message_id:
            return

        member = payload.member
        if member is None:
            member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        verified_role = guild.get_role(verified_role_id)
        if verified_role is None:
            return

        try:
            await member.add_roles(verified_role, reason="Verified by reaction")
        except (discord.Forbidden, discord.HTTPException):
            return

        if unverified_role_id is None:
            return

        unverified_role = guild.get_role(unverified_role_id)
        if unverified_role is None:
            return

        try:
            await member.remove_roles(unverified_role, reason="Removed unverified role after verification")
        except (discord.Forbidden, discord.HTTPException):
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationService(bot))
