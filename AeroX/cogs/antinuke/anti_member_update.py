import discord
from discord.ext import commands
import aiosqlite
import asyncio
import datetime
import pytz
from utils.Tools import strip_and_ban_executor, check_action_bypass

class AntiMemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_limits = {}

    async def is_blacklisted_guild(self, guild_id):
        try:
            async with aiosqlite.connect('db/block.db') as block_db:
                cursor = await block_db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (str(guild_id),))
                return await cursor.fetchone() is not None
        except Exception:
            return False

    async def fetch_audit_logs(self, guild, action, target_id):
        if not guild.me.guild_permissions.view_audit_log and not guild.me.guild_permissions.administrator:
            return None
        try:
            async for entry in guild.audit_logs(action=action, limit=6):
                if entry.target and entry.target.id == target_id:
                    now = datetime.datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() <= 120:
                        return entry
        except Exception:
            pass
        return None

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = before.guild
        if not guild.me.guild_permissions.ban_members:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if not antinuke_status or not antinuke_status[0]:
                return

        # ------------------ TIMEOUT DETECTION ------------------
        now_timed_out = after.is_timed_out()
        was_timed_out = before.is_timed_out()
        timeout_changed = after.timed_out_until != before.timed_out_until

        if now_timed_out and (not was_timed_out or timeout_changed):
            log_entry = await self.fetch_audit_logs(guild, discord.AuditLogAction.member_update, after.id)
            if log_entry is not None:
                executor = log_entry.user

                # Allow bot itself and server owner
                if executor.id == self.bot.user.id or executor.id == guild.owner_id:
                    pass
                elif executor.bot:
                    # ANY other bot performing timeout -> INSTANT BAN
                    await self.revert_timeout_and_ban(after, executor, "Bot Timeout Action | Strict Antinuke")
                    return
                else:
                    if not await check_action_bypass(guild, executor, 'memup'):
                        await self.revert_timeout_and_ban(after, executor, "Member Timeout Action | Unwhitelisted User")
                        return

        # ------------------ ROLE UPDATE DETECTION ------------------
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]

            if added_roles or removed_roles:
                log_entry = await self.fetch_audit_logs(guild, discord.AuditLogAction.member_role_update, after.id)
                if log_entry is not None:
                    executor = log_entry.user

                    if executor.id == self.bot.user.id or executor.id == guild.owner_id:
                        return

                    # Any other bot modifying roles -> INSTANT BAN
                    if executor.bot:
                        await self.revert_roles_and_ban(after, executor, added_roles, removed_roles, "Bot Role Modification | Strict Antinuke")
                        return

                    is_safe = await check_action_bypass(guild, executor, 'memup')

                    # Only Owner or Extra Owner can grant Administrator or registered Bypass roles
                    async with aiosqlite.connect('db/anti.db') as db:
                        async with db.execute("SELECT role_id FROM bypass_roles WHERE guild_id = ?", (guild.id,)) as cursor:
                            bp_roles = {r[0] for r in await cursor.fetchall()}
                        async with db.execute("SELECT role_id FROM action_bypass_roles WHERE guild_id = ?", (guild.id,)) as cursor:
                            bp_roles.update(r[0] for r in await cursor.fetchall())

                    has_bp_or_admin = any(r.permissions.administrator or r.id in bp_roles for r in added_roles)
                    is_owner_or_extra = await check_action_bypass(guild, executor, 'all')

                    if has_bp_or_admin and not is_owner_or_extra:
                        await self.revert_roles_and_ban(after, executor, added_roles, removed_roles, "Unauthorized attempt to grant Administrator or Bypass role | Instant Ban")
                        return

                    if not is_safe:
                        await self.revert_roles_and_ban(after, executor, added_roles, removed_roles, "Member Role Modification | Unwhitelisted User")
                        return

    async def revert_timeout_and_ban(self, member, executor, reason):
        # 1. Untimeout the victim
        try:
            await member.edit(timed_out_until=None, reason=f"Reverting unauthorized timeout by {executor} ({executor.id})")
        except Exception:
            pass

        # 2. Strip roles, server mute/deafen, and ban executor
        await strip_and_ban_executor(member.guild, executor, reason)

    async def revert_roles_and_ban(self, member, executor, added_roles, removed_roles, reason):
        # Revert added roles
        if added_roles:
            try:
                roles_to_keep = [r for r in member.roles if r not in added_roles]
                await member.edit(roles=roles_to_keep, reason=f"Reverting roles added by {executor}")
            except Exception:
                pass

        # Revert removed roles
        if removed_roles:
            try:
                roles_to_restore = list(member.roles) + [r for r in removed_roles if r not in member.roles]
                await member.edit(roles=roles_to_restore, reason=f"Reverting roles removed by {executor}")
            except Exception:
                pass

        # Strip roles, server mute/deafen, and ban executor
        await strip_and_ban_executor(member.guild, executor, reason)

async def setup(bot):
    await bot.add_cog(AntiMemberUpdate(bot))
