import discord
from discord.ext import commands
import aiosqlite
import asyncio
import datetime
import pytz
from utils.Tools import check_action_bypass

class AntiChannelCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_blacklisted_guild(self, guild_id):
        try:
            async with aiosqlite.connect('db/block.db') as block_db:
                cursor = await block_db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (str(guild_id),))
                return await cursor.fetchone() is not None
        except Exception:
            return False

    async def fetch_audit_logs(self, guild, action, target_id, delay=0):
        if not guild.me.guild_permissions.view_audit_log and not guild.me.guild_permissions.administrator:
            return None
        try:
            if delay:
                await asyncio.sleep(delay)
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and entry.target.id == target_id:
                    now = datetime.datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() <= 120:
                        return entry
        except Exception:
            pass
        return None

    async def delete_channel_and_ban(self, channel, executor, reason, retries=3):
        # 1. Delete created channel
        try:
            await channel.delete(reason=reason)
        except Exception:
            pass

        # 2. Ban executor
        while retries > 0:
            try:
                await channel.guild.ban(executor, reason=reason)
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

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild

        if not guild.me.guild_permissions.ban_members or not guild.me.guild_permissions.manage_channels:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if not antinuke_status or not antinuke_status[0]:
                return

        logs = await self.fetch_audit_logs(guild, discord.AuditLogAction.channel_create, channel.id, delay=1)
        if logs is None:
            return

        executor = logs.user
        if executor.id == self.bot.user.id or executor.id == guild.owner_id:
            return

        # "also ban the bot even it was whitelisted create or delete anything"
        if executor.bot:
            await self.delete_channel_and_ban(channel, executor, "Bot Channel Create | Strict Antinuke Instant Ban")
            return

        # Check bypass (extraowners, whitelist, bypass roles)
        if await check_action_bypass(guild, executor, 'chcr'):
            return

        # Unwhitelisted human
        await self.delete_channel_and_ban(channel, executor, "Channel Create | Unwhitelisted User (Antinuke Instant Ban)")

async def setup(bot):
    await bot.add_cog(AntiChannelCreate(bot))
