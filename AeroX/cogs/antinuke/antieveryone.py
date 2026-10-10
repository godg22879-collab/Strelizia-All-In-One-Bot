import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import timedelta, datetime
import pytz
from utils.Tools import check_action_bypass

class AntiEveryone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_limits = {}

    async def is_blacklisted_guild(self, guild_id):
        try:
            async with aiosqlite.connect('db/block.db') as block_db:
                cursor = await block_db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (str(guild_id),))
                return await cursor.fetchone() is not None
        except Exception:
            return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.webhook_id:
            return

        is_mention_everyone = message.mention_everyone
        is_mass_mention = len(message.mentions) >= 5 or len(message.role_mentions) >= 3 or message.content.count("<@") >= 5
        if not is_mention_everyone and not is_mass_mention:
            return

        guild = message.guild
        if message.author.id == self.bot.user.id or message.author.id == guild.owner_id:
            return

        if await self.is_blacklisted_guild(guild.id):
            return

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()

            if not antinuke_status or not antinuke_status[0]:
                return

            # Bot mentions everyone -> INSTANT BAN (NO WHITELIST BYPASS)
            if message.author.bot:
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    await guild.ban(message.author, reason="Bot Mentioned @everyone/@here | Strict Antinuke Instant Ban")
                except Exception:
                    pass
                await self.delete_everyone_messages(message.channel)
                return

            # Check bypass (extraowners, whitelist, bypass roles)
            if await check_action_bypass(guild, message.author, 'meneve'):
                return

            # Unwhitelisted human -> STRAIGHT BAN
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await guild.ban(message.author, reason="Mentioned @everyone/@here or Mass Mention | Unwhitelisted User (Antinuke Instant Ban)")
            except Exception:
                pass
            await self.delete_everyone_messages(message.channel)

    async def delete_everyone_messages(self, channel):
        retries = 3
        while retries > 0:
            try:
                async for msg in channel.history(limit=50):
                    if msg.mention_everyone:
                        try:
                            await msg.delete()
                        except Exception:
                            pass
                return
            except Exception:
                retries -= 1
                await asyncio.sleep(1)

async def setup(bot):
    await bot.add_cog(AntiEveryone(bot))
