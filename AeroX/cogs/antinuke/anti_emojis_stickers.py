import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime
import pytz
from utils.Tools import check_action_bypass

class AntiEmojisStickers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_blacklisted_guild(self, guild_id):
        try:
            async with aiosqlite.connect('db/block.db') as block_db:
                cursor = await block_db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (str(guild_id),))
                return await cursor.fetchone() is not None
        except Exception:
            return False

    async def fetch_audit_logs(self, guild, action):
        if not guild.me.guild_permissions.view_audit_log and not guild.me.guild_permissions.administrator:
            return None
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                now = datetime.now(pytz.utc)
                if (now - entry.created_at).total_seconds() <= 120:
                    return entry
        except Exception:
            pass
        return None

    async def ban_executor(self, guild, executor, reason):
        retries = 3
        while retries > 0:
            try:
                await guild.ban(executor, reason=reason)
                return
            except Exception:
                retries -= 1
                await asyncio.sleep(1)

    async def is_authorized(self, guild, executor):
        if executor.id == self.bot.user.id:
            return True
        return await check_action_bypass(guild, executor, 'mngstemo')

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if not guild.me.guild_permissions.ban_members:
            return
        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                status = await cursor.fetchone()
            if not status or not status[0]:
                return

        action = None
        created_emojis = []
        if len(after) > len(before):
            action = discord.AuditLogAction.emoji_create
            created_emojis = [e for e in after if e not in before]
        elif len(after) < len(before):
            action = discord.AuditLogAction.emoji_delete
        else:
            action = discord.AuditLogAction.emoji_update

        log = await self.fetch_audit_logs(guild, action)
        if not log:
            return

        executor = log.user
        if await self.is_authorized(guild, executor):
            return

        # Delete unauthorized created emojis
        for emoji in created_emojis:
            try:
                await emoji.delete(reason=f"Unauthorized emoji creation by {executor}")
            except Exception:
                pass

        reason = f"Emoji Action ({action.name}) | Unwhitelisted User / Bot (Antinuke Instant Ban)"
        await self.ban_executor(guild, executor, reason)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        if not guild.me.guild_permissions.ban_members:
            return
        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                status = await cursor.fetchone()
            if not status or not status[0]:
                return

        action = None
        created_stickers = []
        if len(after) > len(before):
            action = discord.AuditLogAction.sticker_create
            created_stickers = [s for s in after if s not in before]
        elif len(after) < len(before):
            action = discord.AuditLogAction.sticker_delete
        else:
            action = discord.AuditLogAction.sticker_update

        log = await self.fetch_audit_logs(guild, action)
        if not log:
            return

        executor = log.user
        if await self.is_authorized(guild, executor):
            return

        for sticker in created_stickers:
            try:
                await sticker.delete(reason=f"Unauthorized sticker creation by {executor}")
            except Exception:
                pass

        reason = f"Sticker Action ({action.name}) | Unwhitelisted User / Bot (Antinuke Instant Ban)"
        await self.ban_executor(guild, executor, reason)

async def setup(bot):
    await bot.add_cog(AntiEmojisStickers(bot))
