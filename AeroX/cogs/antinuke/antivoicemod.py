import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime
import pytz
from utils.Tools import check_action_bypass, strip_and_ban_executor

class AntiVoiceMod(commands.Cog):
    """Detects and punishes unauthorized server mutes and deafens in voice channels."""
    def __init__(self, bot):
        self.bot = bot

    async def is_blacklisted_guild(self, guild_id):
        try:
            async with aiosqlite.connect('db/block.db') as block_db:
                cursor = await block_db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (str(guild_id),))
                return await cursor.fetchone() is not None
        except Exception:
            return False

    async def fetch_audit_logs(self, guild, target_id):
        if not guild.me.guild_permissions.view_audit_log and not guild.me.guild_permissions.administrator:
            return None
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update, limit=5):
                if entry.target and entry.target.id == target_id:
                    now = datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() <= 120:
                        return entry
        except Exception:
            pass
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        if not guild.me.guild_permissions.ban_members:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        # Check if server mute or deafen was applied
        mute_applied = not before.mute and after.mute
        deaf_applied = not before.deaf and after.deaf

        if not mute_applied and not deaf_applied:
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                status = await cursor.fetchone()
            if not status or not status[0]:
                return

        log = await self.fetch_audit_logs(guild, member.id)
        if not log:
            return

        executor = log.user
        if executor.id == self.bot.user.id or executor.id == guild.owner_id:
            return

        # If executor is a bot -> Instant Ban (No whitelist bypass for bots)
        if executor.bot:
            # 1. Untarget victim
            try:
                await member.edit(mute=False, deafen=False, reason="Reverting unauthorized bot voice moderation")
            except Exception:
                pass
            # 2. Strip roles and ban
            await strip_and_ban_executor(guild, executor, "Bot Server Mute/Deafen | Strict Antinuke Instant Ban")
            return

        # Check human authorization
        if await check_action_bypass(guild, executor, 'voicemod') or await check_action_bypass(guild, executor, 'memup'):
            return

        # Unwhitelisted human -> Revert victim + Strip executor roles + Ban!
        try:
            await member.edit(mute=False, deafen=False, reason=f"Reverting unauthorized voice moderation by {executor}")
        except Exception:
            pass

        await strip_and_ban_executor(guild, executor, "Server Mute / Deafen Action | Unwhitelisted User (Antinuke Instant Ban)")

async def setup(bot):
    await bot.add_cog(AntiVoiceMod(bot))
