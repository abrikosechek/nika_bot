from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config_manager


LOCKED_PREFIX = "🔒"
UNLOCKED_PREFIX = "🔓"
DEFAULT_LIMIT = 10
MIN_LIMIT = 2
MAX_LIMIT = 20
CLAIM_TIMEOUT = timedelta(minutes=10)


@dataclass
class RoomState:
    channel_id: int
    owner_id: int
    name: str
    is_locked: bool = False
    user_limit: int = DEFAULT_LIMIT
    banned_user_ids: set[int] = field(default_factory=set)
    owner_left_at: datetime | None = None


class PrivateRooms(commands.Cog):
    private = app_commands.Group(name="private", description="Управление приватной комнатой")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rooms_by_channel_id: dict[int, RoomState] = {}
        self.owner_to_room_channel_id: dict[int, int] = {}

    def _get_private_config(self, guild_id: int | None) -> dict | None:
        if guild_id is None:
            return None
        return config_manager.get_category(guild_id, "private")

    def _format_channel_name(self, room: RoomState) -> str:
        prefix = LOCKED_PREFIX if room.is_locked else UNLOCKED_PREFIX
        return f"{prefix} {room.name}"

    async def _respond(self, interaction: discord.Interaction, text: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)

    async def _command_guard(self, interaction: discord.Interaction) -> tuple[bool, str | None]:
        if interaction.guild is None:
            return False, "Ошибка: команда доступна только на сервере."

        private_config = self._get_private_config(interaction.guild_id)
        if private_config is None:
            return False, "Ошибка: приватный модуль не настроен для этого сервера."

        control_channel_id = private_config.get("control_text_channel")
        if interaction.channel_id != control_channel_id:
            return (
                False,
                f"Ошибка: эту команду можно использовать только в <#{control_channel_id}>.",
            )

        return True, None

    def _get_owner_room(self, owner_id: int) -> RoomState | None:
        room_channel_id = self.owner_to_room_channel_id.get(owner_id)
        if room_channel_id is None:
            return None
        return self.rooms_by_channel_id.get(room_channel_id)

    def _get_member_current_room(self, member: discord.Member) -> RoomState | None:
        if member.voice is None or member.voice.channel is None:
            return None
        return self.rooms_by_channel_id.get(member.voice.channel.id)

    async def _apply_room_overwrites(self, guild: discord.Guild, channel: discord.VoiceChannel, room: RoomState) -> None:
        everyone_overwrite = discord.PermissionOverwrite()
        everyone_overwrite.connect = False if room.is_locked else None
        await channel.set_permissions(guild.default_role, overwrite=everyone_overwrite)

        owner = guild.get_member(room.owner_id)
        if owner is not None:
            await channel.set_permissions(
                owner,
                connect=True,
                view_channel=True,
                speak=True,
            )

        for banned_user_id in room.banned_user_ids:
            banned_member = guild.get_member(banned_user_id)
            if banned_member is not None:
                await channel.set_permissions(banned_member, connect=False)

    async def _delete_room(self, guild: discord.Guild, room: RoomState) -> None:
        channel = guild.get_channel(room.channel_id)
        if isinstance(channel, discord.VoiceChannel):
            try:
                await channel.delete(reason="Private room cleanup")
            except discord.HTTPException:
                pass
        self.rooms_by_channel_id.pop(room.channel_id, None)
        self.owner_to_room_channel_id.pop(room.owner_id, None)

    async def _ensure_private_room(self, member: discord.Member) -> discord.VoiceChannel | None:
        existing_room = self._get_owner_room(member.id)
        if existing_room is not None:
            existing_channel = member.guild.get_channel(existing_room.channel_id)
            if isinstance(existing_channel, discord.VoiceChannel):
                return existing_channel
            # stale state cleanup
            self.rooms_by_channel_id.pop(existing_room.channel_id, None)
            self.owner_to_room_channel_id.pop(member.id, None)

        room = RoomState(
            channel_id=0,
            owner_id=member.id,
            name=member.display_name,
            user_limit=DEFAULT_LIMIT,
        )

        private_config = self._get_private_config(member.guild.id) or {}
        category_id = private_config.get("rooms_category")
        category = member.guild.get_channel(category_id) if category_id is not None else None
        if not isinstance(category, discord.CategoryChannel):
            category = None

        channel = await member.guild.create_voice_channel(
            name=self._format_channel_name(room),
            user_limit=room.user_limit,
            category=category,
            reason="Create private room",
        )

        room.channel_id = channel.id
        self.rooms_by_channel_id[channel.id] = room
        self.owner_to_room_channel_id[member.id] = channel.id
        await self._apply_room_overwrites(member.guild, channel, room)
        return channel

    async def _handle_follow_voice_router(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        follow_cog = self.bot.get_cog("VoiceFollower")
        if follow_cog is None:
            return

        handler = getattr(follow_cog, "handle_voice_state_update", None)
        if handler is None:
            return

        await handler(member, before, after)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        # Router branch: existing follow feature.
        await self._handle_follow_voice_router(member, before, after)

        # Router branch: private rooms lifecycle.
        private_config = self._get_private_config(member.guild.id)
        if private_config is None:
            return

        create_voice_channel_id = private_config.get("create_voice_channel")
        if create_voice_channel_id is None:
            return

        joined_create_channel = (
            after.channel is not None
            and after.channel.id == create_voice_channel_id
            and (before.channel is None or before.channel.id != create_voice_channel_id)
        )

        if joined_create_channel:
            try:
                room_channel = await self._ensure_private_room(member)
                if room_channel is not None:
                    await member.move_to(room_channel, reason="Join personal private room")
            except discord.HTTPException:
                pass
            return

        if before.channel is not None:
            previous_room = self.rooms_by_channel_id.get(before.channel.id)
            if previous_room is not None:
                is_owner_left_room = previous_room.owner_id == member.id and (
                    after.channel is None or after.channel.id != before.channel.id
                )
                if is_owner_left_room and len(before.channel.members) > 0:
                    previous_room.owner_left_at = datetime.now(timezone.utc)

                human_members = [m for m in before.channel.members if not m.bot]
                if len(human_members) == 0:
                    await self._delete_room(member.guild, previous_room)
                    return

        if after.channel is not None:
            current_room = self.rooms_by_channel_id.get(after.channel.id)
            if current_room is not None and current_room.owner_id == member.id:
                current_room.owner_left_at = None

    @private.command(name="lock", description="Закрыть свою приватную комнату")
    async def lock(self, interaction: discord.Interaction) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            room.is_locked = True
            await self._apply_room_overwrites(interaction.guild, channel, room)
            await channel.edit(name=self._format_channel_name(room))
            await self._respond(interaction, "Комната закрыта.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось закрыть комнату.")

    @private.command(name="unlock", description="Открыть свою приватную комнату")
    async def unlock(self, interaction: discord.Interaction) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            room.is_locked = False
            await self._apply_room_overwrites(interaction.guild, channel, room)
            await channel.edit(name=self._format_channel_name(room))
            await self._respond(interaction, "Комната открыта.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось открыть комнату.")

    @private.command(name="limit", description="Изменить лимит участников своей комнаты")
    async def limit(self, interaction: discord.Interaction, value: app_commands.Range[int, MIN_LIMIT, MAX_LIMIT]) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            if len(channel.members) > value:
                await self._respond(
                    interaction,
                    "Ошибка: лимит нельзя сделать меньше текущего числа участников в комнате.",
                )
                return

            room.user_limit = value
            await channel.edit(user_limit=value)
            await self._respond(interaction, f"Лимит комнаты обновлен: {value}.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось изменить лимит комнаты.")

    @private.command(name="kick", description="Выгнать пользователя из своей комнаты")
    async def kick(self, interaction: discord.Interaction, user: discord.Member) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            if user.id == interaction.user.id:
                await self._respond(interaction, "Ошибка: нельзя кикнуть самого себя.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            if user.voice is None or user.voice.channel is None or user.voice.channel.id != channel.id:
                await self._respond(interaction, "Ошибка: пользователь не находится в вашей комнате.")
                return

            await user.move_to(None, reason=f"Kicked from private room by {interaction.user.id}")
            await self._respond(interaction, f"Пользователь {user.mention} выгнан из комнаты.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось кикнуть пользователя.")

    @private.command(name="ban", description="Забанить пользователя в своей комнате")
    async def ban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            if user.id == interaction.user.id:
                await self._respond(interaction, "Ошибка: нельзя забанить самого себя.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            room.banned_user_ids.add(user.id)
            await channel.set_permissions(user, connect=False)

            if user.voice is not None and user.voice.channel is not None and user.voice.channel.id == channel.id:
                await user.move_to(None, reason=f"Banned from private room by {interaction.user.id}")

            await self._respond(interaction, f"Пользователь {user.mention} забанен для этой комнаты.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось забанить пользователя.")

    @private.command(name="unban", description="Снять бан пользователя в своей комнате")
    async def unban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            if user.id not in room.banned_user_ids:
                await self._respond(interaction, "Ошибка: этот пользователь не был забанен в вашей комнате.")
                return

            room.banned_user_ids.discard(user.id)
            await channel.set_permissions(user, overwrite=None)
            await self._apply_room_overwrites(interaction.guild, channel, room)
            await self._respond(interaction, f"Бан для {user.mention} снят.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось снять бан пользователя.")

    @private.command(name="close", description="Удалить свою приватную комнату")
    async def close(self, interaction: discord.Interaction) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            for member in list(channel.members):
                try:
                    await member.move_to(None, reason=f"Private room closed by {interaction.user.id}")
                except discord.HTTPException:
                    pass

            await self._delete_room(interaction.guild, room)
            await self._respond(interaction, "Комната закрыта и удалена.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось закрыть комнату.")

    @private.command(name="claim", description="Забрать ownership комнаты после отсутствия owner")
    async def claim(self, interaction: discord.Interaction) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            if self._get_owner_room(interaction.user.id) is not None:
                await self._respond(interaction, "Ошибка: у вас уже есть своя приватная комната.")
                return

            if not isinstance(interaction.user, discord.Member):
                await self._respond(interaction, "Ошибка: не удалось определить участника сервера.")
                return

            room = self._get_member_current_room(interaction.user)
            if room is None:
                await self._respond(interaction, "Ошибка: вы должны находиться в приватной комнате для claim.")
                return

            if room.owner_id == interaction.user.id:
                await self._respond(interaction, "Ошибка: вы уже владелец этой комнаты.")
                return

            if room.owner_left_at is None:
                await self._respond(interaction, "Ошибка: owner комнаты не отсутствует достаточное время.")
                return

            if datetime.now(timezone.utc) - room.owner_left_at < CLAIM_TIMEOUT:
                await self._respond(interaction, "Ошибка: claim доступен только через 10 минут после выхода owner.")
                return

            channel = interaction.guild.get_channel(room.channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await self._respond(interaction, "Ошибка: канал комнаты не найден.")
                return

            self.owner_to_room_channel_id.pop(room.owner_id, None)
            room.owner_id = interaction.user.id
            room.owner_left_at = None
            self.owner_to_room_channel_id[interaction.user.id] = room.channel_id
            await self._apply_room_overwrites(interaction.guild, channel, room)

            await self._respond(interaction, "Ownership комнаты успешно передан вам.")
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось выполнить claim.")

    @private.command(name="info", description="Показать информацию о своей приватной комнате")
    async def info(self, interaction: discord.Interaction) -> None:
        try:
            ok, reason = await self._command_guard(interaction)
            if not ok:
                await self._respond(interaction, reason)
                return

            room = self._get_owner_room(interaction.user.id)
            if room is None:
                await self._respond(interaction, "Ошибка: у вас нет своей приватной комнаты.")
                return

            owner_left_at_text = (
                room.owner_left_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                if room.owner_left_at
                else "owner в комнате / owner недавно вернулся"
            )

            channel = interaction.guild.get_channel(room.channel_id)
            members_count = len(channel.members) if isinstance(channel, discord.VoiceChannel) else "n/a"

            banned_list = ", ".join(str(user_id) for user_id in sorted(room.banned_user_ids)) or "нет"
            state_text = "закрыта" if room.is_locked else "открыта"

            text = (
                f"Комната: `{self._format_channel_name(room)}`\n"
                f"Owner ID: `{room.owner_id}`\n"
                f"Состояние: `{state_text}`\n"
                f"Лимит: `{room.user_limit}`\n"
                f"Участники сейчас: `{members_count}`\n"
                f"Banned users: `{banned_list}`\n"
                f"Owner left at: `{owner_left_at_text}`"
            )
            await self._respond(interaction, text)
        except Exception:
            await self._respond(interaction, "Ошибка: не удалось получить информацию о комнате.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrivateRooms(bot))
