import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime
import pytz
from utils.Tools import check_action_bypass

class AntiUnban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_audit_logs(self, guild, action, target_id):
        if not guild.me.guild_permissions.view_audit_log and not guild.me.guild_permissions.administrator:
            return None
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target and entry.target.id == target_id:
                    now = datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() <= 120:
                        return entry
        except Exception:
            pass
        return None

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if not guild.me.guild_permissions.ban_members:
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()

            if not antinuke_status or not antinuke_status[0]:
                return

            log_entry = await self.fetch_audit_logs(guild, discord.AuditLogAction.unban, user.id)
            if log_entry is None:
                return

            executor = log_entry.user

            if executor.id in {guild.owner_id, self.bot.user.id}:
                return

            # Bot unbans someone -> INSTANT BAN (NO WHITELIST BYPASS)
            if executor.bot:
                await self.ban_executor(guild, executor, user, "Bot Unban Action | Strict Antinuke Instant Ban")
                return

            if await check_action_bypass(guild, executor, 'ban'):
                return

            # Unwhitelisted human -> STRAIGHT BAN
            await self.ban_executor(guild, executor, user, "Member Unban | Unwhitelisted User (Antinuke Instant Ban)")

    async def ban_executor(self, guild, executor, user, reason):
        retries = 3
        while retries > 0:
            try:
                await guild.ban(executor, reason=reason)
                await guild.ban(user, reason="Reverting unban by unwhitelisted user / bot")
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
    await bot.add_cog(AntiUnban(bot))
