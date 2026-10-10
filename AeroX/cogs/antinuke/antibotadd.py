import discord
from discord.ext import commands
import aiosqlite
import asyncio
import datetime
import pytz
from utils.Tools import check_action_bypass, strip_and_ban_executor

class AntiBotAdd(commands.Cog):
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
        for _ in range(5):
            try:
                async for entry in guild.audit_logs(action=action, limit=6):
                    if entry.target and entry.target.id == target_id:
                        now = datetime.datetime.now(pytz.utc)
                        if (now - entry.created_at).total_seconds() <= 120:
                            return entry
            except Exception:
                pass
            await asyncio.sleep(0.8)
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot:
            return

        guild = member.guild
        if not guild.me.guild_permissions.ban_members:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if not antinuke_status or not antinuke_status[0]:
                return

        logs = await self.fetch_audit_logs(guild, discord.AuditLogAction.bot_add, member.id)
        if logs is None:
            # Fallback if audit log not found: ban the unauthorized bot
            try:
                await guild.ban(member, reason="Unauthorized Bot Join | Strict Antinuke")
            except Exception:
                pass
            return

        executor = logs.user

        # Never touch this bot itself
        if executor.id == self.bot.user.id or member.id == self.bot.user.id:
            return

        # Check if executor is authorized / bypassed
        if await check_action_bypass(guild, executor, 'all'):
            if executor.id == guild.owner_id:
                await self.ban_bot_only(guild, member, "Bot added by Server Owner | Strict Bot Ban Policy")
            return

        # Unauthorized adder -> BAN BOTH (ban bot and ban the adder)
        await self.ban_both(guild, executor, member, f"Unauthorized Bot Add by {executor} ({executor.id})")

    async def ban_bot_only(self, guild, bot_member, reason):
        retries = 3
        while retries > 0:
            try:
                await guild.ban(bot_member, reason=reason)
                return
            except discord.Forbidden:
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.response.headers.get('Retry-After')
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                        retries -= 1
                    else:
                        break
                else:
                    return
            except Exception:
                return

    async def ban_both(self, guild, executor, bot_member, reason):
        # 1. Ban the added bot
        await self.ban_bot_only(guild, bot_member, reason)

        # 2. Ban the adder who invited the unauthorized bot
        await strip_and_ban_executor(guild, executor, f"Unauthorized Bot Add: invited {bot_member} ({bot_member.id})")

async def setup(bot):
    await bot.add_cog(AntiBotAdd(bot))
