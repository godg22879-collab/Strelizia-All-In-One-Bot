import discord
from discord.ext import commands
import aiosqlite
import asyncio
import datetime
import pytz
from utils.Tools import check_action_bypass

class AntiRoleUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and entry.target.id == target_id:
                    now = datetime.datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() <= 120:
                        return entry
        except Exception:
            pass
        return None

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = before.guild
        if not guild.me.guild_permissions.ban_members or not guild.me.guild_permissions.manage_roles:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if not antinuke_status or not antinuke_status[0]:
                return

        log_entry = await self.fetch_audit_logs(guild, discord.AuditLogAction.role_update, before.id)
        if log_entry is None:
            return

        executor = log_entry.user

        if executor.id in {guild.owner_id, self.bot.user.id}:
            return

        # ------------------ @everyone ROLE TAMPERING PROTECTION ------------------
        if after == guild.default_role:
            # Dangerous perms check on @everyone
            dangerous = [
                after.permissions.administrator,
                after.permissions.ban_members,
                after.permissions.kick_members,
                after.permissions.manage_channels,
                after.permissions.manage_roles,
                after.permissions.manage_guild,
                after.permissions.manage_webhooks,
                after.permissions.mention_everyone,
                after.permissions.moderate_members
            ]
            if any(dangerous):
                # Immediate Ban - No whitelist bypass for giving perms to @everyone
                await self.ban_executor_and_revert_role_update(guild, executor, before, after, "Dangerous Permissions added to @everyone role | Instant Ban")
                return

        # ------------------ BOT ROLE UPDATE ------------------
        if executor.bot:
            await self.ban_executor_and_revert_role_update(guild, executor, before, after, "Bot Role Update | Strict Antinuke Instant Ban")
            return

        # ------------------ HUMAN EXECUTOR CHECK ------------------
        if await check_action_bypass(guild, executor, 'rlup'):
            # If bypass user added Administrator to a role, only extraowner/owner can do that
            if not before.permissions.administrator and after.permissions.administrator:
                await self.ban_executor_and_revert_role_update(guild, executor, before, after, "Admin permission added to role without Owner authorization")
                return
            return

        # Unwhitelisted human -> STRAIGHT BAN
        await self.ban_executor_and_revert_role_update(guild, executor, before, after, "Role Update | Unwhitelisted User (Antinuke Instant Ban)")

    async def ban_executor_and_revert_role_update(self, guild, executor, before, after, reason):
        retries = 3
        while retries > 0:
            try:
                # 1. Ban executor
                await self.ban_executor(guild, executor, reason)
                # 2. Revert role
                await after.edit(
                    name=before.name,
                    permissions=before.permissions,
                    color=before.color,
                    hoist=before.hoist,
                    mentionable=before.mentionable,
                    reason=f"Reverting role update by {executor}"
                )
                return
            except discord.Forbidden:
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.response.headers.get('Retry-After', 1)
                    await asyncio.sleep(float(retry_after))
                    retries -= 1
                else:
                    return
            except Exception:
                return

    async def ban_executor(self, guild, executor, reason):
        retries = 3
        while retries > 0:
            try:
                await guild.ban(executor, reason=reason)
                return
            except discord.Forbidden:
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.response.headers.get('Retry-After', 1)
                    await asyncio.sleep(float(retry_after))
                    retries -= 1
                else:
                    return
            except Exception:
                return

async def setup(bot):
    await bot.add_cog(AntiRoleUpdate(bot))
