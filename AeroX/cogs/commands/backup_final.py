import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
from datetime import datetime, timedelta
import random
import string
import aiohttp
import asyncio
import logging
import json
import io
import os
import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "db/backups.db"
OWNER_IDS = [1542661619245383683, 1542645079993483266, 1124248109472550993]

def generate_backup_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class Backup(commands.Cog):
    """24/7 Automated and Manual Server Backup & Restoration System"""
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.auto_backup_loop.start()
        bot.loop.create_task(self.init_db())

    async def init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    guild_id INTEGER,
                    guild_name TEXT,
                    creator_id INTEGER,
                    created_at TEXT,
                    roles TEXT,
                    categories TEXT,
                    channels TEXT,
                    emojis TEXT,
                    is_auto INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS auto_backup_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER DEFAULT 0,
                    interval_hours INTEGER DEFAULT 24,
                    last_backup TEXT
                )
            """)
            await db.commit()

    async def cog_unload(self):
        self.auto_backup_loop.cancel()
        await self.session.close()
        logger.info("Backup cog unloaded.")

    def is_admin(self, ctx):
        if ctx.guild and (ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner):
            return True
        return ctx.author.id in OWNER_IDS

    def is_owner(self, user_id):
        return user_id in OWNER_IDS

    async def post_status(self, dest, msg, color=0x000000):
        embed = discord.Embed(description=msg, color=color)
        try:
            await dest.send(embed=embed)
        except discord.HTTPException as e:
            logger.warning(f"Failed to send status: {e}")

    async def safe_delete(self, obj, status_channel):
        if isinstance(obj, discord.Role):
            bot_member = status_channel.guild.get_member(self.bot.user.id)
            if bot_member and obj == bot_member.top_role:
                return
        try:
            await obj.delete()
            await asyncio.sleep(0.4)
        except discord.HTTPException as e:
            await self.post_status(status_channel, f"<:icon_danger:1372375135604047902> Failed to delete {obj}: {e}", 0x000000)

    async def create_emoji_with_retry(self, guild, name, image, status, retries=3):
        for attempt in range(retries):
            try:
                await guild.create_custom_emoji(name=name, image=image)
                await asyncio.sleep(0.5)
                return True
            except discord.HTTPException as e:
                if e.status == 429 and attempt < retries - 1:
                    retry_after = getattr(e, "retry_after", 5)
                    await self.post_status(status, f"<:icon_danger:1372375135604047902> Rate limit on emoji {name}, retrying in {retry_after}s...", 0x000000)
                    await asyncio.sleep(retry_after)
                    continue
                await self.post_status(status, f"<:icon_danger:1372375135604047902> Failed to create emoji {name}: {e}", 0x000000)
                return False

    async def serialize_guild(self, guild):
        roles = [
            {
                "id": r.id,
                "name": r.name,
                "permissions": r.permissions.value,
                "color": r.color.value,
                "hoist": r.hoist,
                "mentionable": r.mentionable,
                "position": r.position
            }
            for r in guild.roles if not r.is_default()
        ]
        categories = [{"name": c.name, "position": c.position} for c in guild.categories]
        channels = []
        for cat in guild.categories:
            for ch in cat.channels:
                overwrites = [
                    {
                        "id": t.id,
                        "type": "role" if isinstance(t, discord.Role) else "member",
                        "allow": p.pair()[0].value,
                        "deny": p.pair()[1].value
                    }
                    for t, p in ch.overwrites.items()
                ]
                if isinstance(ch, discord.TextChannel):
                    channels.append({
                        "name": ch.name,
                        "type": "text",
                        "topic": ch.topic,
                        "slowmode": ch.slowmode_delay,
                        "nsfw": ch.nsfw,
                        "category": cat.name,
                        "overwrites": overwrites
                    })
                elif isinstance(ch, discord.VoiceChannel):
                    channels.append({
                        "name": ch.name,
                        "type": "voice",
                        "bitrate": min(ch.bitrate, 96000),
                        "user_limit": ch.user_limit,
                        "category": cat.name,
                        "overwrites": overwrites
                    })
        # Guild level channels without category
        for ch in guild.channels:
            if ch.category is None:
                overwrites = [
                    {
                        "id": t.id,
                        "type": "role" if isinstance(t, discord.Role) else "member",
                        "allow": p.pair()[0].value,
                        "deny": p.pair()[1].value
                    }
                    for t, p in ch.overwrites.items()
                ]
                if isinstance(ch, discord.TextChannel):
                    channels.append({
                        "name": ch.name,
                        "type": "text",
                        "topic": ch.topic,
                        "slowmode": ch.slowmode_delay,
                        "nsfw": ch.nsfw,
                        "category": None,
                        "overwrites": overwrites
                    })
                elif isinstance(ch, discord.VoiceChannel):
                    channels.append({
                        "name": ch.name,
                        "type": "voice",
                        "bitrate": min(ch.bitrate, 96000),
                        "user_limit": ch.user_limit,
                        "category": None,
                        "overwrites": overwrites
                    })

        emojis = [{"name": e.name, "url": str(e.url)} for e in guild.emojis]
        return roles, categories, channels, emojis

    @tasks.loop(minutes=15)
    async def auto_backup_loop(self):
        """24/7 Background task that automatically creates snapshots for guilds with auto-backup enabled"""
        await self.bot.wait_until_ready()
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT guild_id, interval_hours, last_backup FROM auto_backup_settings WHERE enabled = 1") as cursor:
                    rows = await cursor.fetchall()

                now = datetime.utcnow()
                for guild_id, interval_hours, last_backup in rows:
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue

                    should_backup = False
                    if not last_backup:
                        should_backup = True
                    else:
                        try:
                            last_time = datetime.fromisoformat(last_backup)
                            if (now - last_time).total_seconds() >= (interval_hours * 3600):
                                should_backup = True
                        except Exception:
                            should_backup = True

                    if should_backup:
                        try:
                            roles, categories, channels, emojis = await self.serialize_guild(guild)
                            b_id = generate_backup_id()
                            await db.execute("""
                                INSERT INTO backups (backup_id, guild_id, guild_name, creator_id, created_at, roles, categories, channels, emojis, is_auto)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                            """, (
                                b_id, guild.id, guild.name, guild.owner_id or 0,
                                now.isoformat(), json.dumps(roles), json.dumps(categories),
                                json.dumps(channels), json.dumps(emojis)
                            ))
                            await db.execute("UPDATE auto_backup_settings SET last_backup = ? WHERE guild_id = ?", (now.isoformat(), guild.id))
                            await db.commit()
                            logger.info(f"[24/7 Auto-Backup] Created snapshot for guild '{guild.name}' ({guild.id}) with ID {b_id}")
                        except Exception as e:
                            logger.error(f"[24/7 Auto-Backup Error]: {e}")
        except Exception as e:
            logger.error(f"[Auto Backup Loop Exception]: {e}")

    @commands.hybrid_group(
        name="backup",
        aliases=['bk', 'bak', 'serverbackup', 'backups'],
        description="24/7 Server Backup and restoration commands",
        invoke_without_command=True
    )
    async def backup(self, ctx):
        await ctx.send_help(ctx.command)

    @backup.command(name="create", aliases=['c', 'make', 'new'], description="Create a new server backup")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def create(self, ctx):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        guild = ctx.guild
        if not guild:
            return await ctx.send("<:icon_cross:1372375094336425986> This command must be run in a server.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM backups WHERE creator_id = ?", (ctx.author.id,)) as cursor:
                count_row = await cursor.fetchone()
                user_count = count_row[0] if count_row else 0

            if user_count >= 10 and not self.is_owner(ctx.author.id):
                async with db.execute("SELECT backup_id, guild_name FROM backups WHERE creator_id = ? LIMIT 10", (ctx.author.id,)) as c2:
                    user_backups = await c2.fetchall()
                embed = discord.Embed(
                    title="🚫 Backup Limit Reached",
                    color=0x000000,
                    description="**You've reached the maximum limit of 10 backups!**\n*Delete an old backup using `backup delete <id>` to create a new one.*"
                )
                embed.add_field(
                    name="📦 Your Current Backups",
                    value="\n".join(f"🔹 `{b[0]}` - *{b[1]}*" for b in user_backups) or "None",
                    inline=False
                )
                return await ctx.send(embed=embed)

            backup_id = generate_backup_id()
            roles, categories, channels, emojis = await self.serialize_guild(guild)
            now_iso = datetime.utcnow().isoformat()

            await db.execute("""
                INSERT INTO backups (backup_id, guild_id, guild_name, creator_id, created_at, roles, categories, channels, emojis, is_auto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                backup_id, guild.id, guild.name, ctx.author.id,
                now_iso, json.dumps(roles), json.dumps(categories),
                json.dumps(channels), json.dumps(emojis)
            ))
            await db.commit()

        embed = discord.Embed(
            title="✅ 𝐁𝐚𝐜𝐤𝐮𝐩 𝐂𝐫𝐞𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!",
            color=0x000000,
            description=f"**Your 24/7 server backup is safely secured!**\n\n🆔 **Backup ID:** `{backup_id}`"
        )
        embed.add_field(
            name="📊 Backup Contents",
            value=f"🎭 **{len(roles)}** roles\n📁 **{len(categories)}** categories\n📺 **{len(channels)}** channels\n😀 **{len(emojis)}** emojis",
            inline=True
        )
        embed.add_field(
            name="🏠 Server Details",
            value=f"**{guild.name}**\n👑 Created by {ctx.author.mention}\n⚡ **Storage:** Local 24/7 Database",
            inline=True
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"💾 Restore anytime with: &backup load {backup_id}")
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @backup.command(name="auto", aliases=['247', 'schedule', 'autobackup'], description="Configure 24/7 automated scheduled backups")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def auto_backup(self, ctx, toggle: str = None, interval_hours: int = 24):
        """Enable or disable 24/7 automated backups for this server"""
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        guild = ctx.guild
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled, interval_hours, last_backup FROM auto_backup_settings WHERE guild_id = ?", (guild.id,)) as cursor:
                row = await cursor.fetchone()

            if toggle is None:
                is_on = row and row[0] == 1
                curr_interval = row[1] if row else 24
                last_bk = row[2] if row and row[2] else "None"
                embed = discord.Embed(
                    title="🕒 𝟐𝟒/𝟕 𝐀𝐮𝐭𝐨𝐦𝐚𝐭𝐞𝐝 𝐁𝐚𝐜𝐤𝐮𝐩 𝐒𝐭𝐚𝐭𝐮𝐬",
                    color=0x000000,
                    description=f"**Server:** {guild.name}\n**Status:** {'🟢 **Enabled (Active 24/7)**' if is_on else '🔴 **Disabled**'}\n**Interval:** Every `{curr_interval}` hours\n**Last Backup:** `{last_bk}`\n\n💡 *Use `&backup auto on [hours]` or `&backup auto off` to configure.*"
                )
                return await ctx.send(embed=embed)

            if toggle.lower() in ['on', 'enable', 'true', '1']:
                interval = max(1, min(168, interval_hours))
                await db.execute("""
                    INSERT INTO auto_backup_settings (guild_id, enabled, interval_hours, last_backup)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET enabled = 1, interval_hours = excluded.interval_hours
                """, (guild.id, interval, datetime.utcnow().isoformat()))
                await db.commit()
                embed = discord.Embed(
                    title="🟢 𝟐𝟒/𝟕 𝐀𝐮𝐭𝐨-𝐁𝐚𝐜𝐤𝐮𝐩 𝐀𝐜𝐭𝐢𝐯𝐚𝐭𝐞𝐝",
                    color=0x000000,
                    description=f"**Automated backups are now active 24/7!**\n\n⏱️ A full server snapshot will be taken automatically every **{interval} hours**.\nYour server structure is continuously protected."
                )
                return await ctx.send(embed=embed)

            elif toggle.lower() in ['off', 'disable', 'false', '0']:
                await db.execute("UPDATE auto_backup_settings SET enabled = 0 WHERE guild_id = ?", (guild.id,))
                await db.commit()
                embed = discord.Embed(
                    title="🔴 𝟐𝟒/𝟕 𝐀𝐮𝐭𝐨-𝐁𝐚𝐜𝐤𝐮𝐩 𝐃𝐞𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞𝐝",
                    color=0x000000,
                    description="Automated backups have been turned off for this server."
                )
                return await ctx.send(embed=embed)
            else:
                return await ctx.send("<:icon_cross:1372375094336425986> Invalid option. Use `on` or `off` (e.g. `&backup auto on 12`).")

    @backup.command(name="list", aliases=['ls', 'all'], description="List all your server backups")
    async def list_backups(self, ctx):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT backup_id, guild_name, created_at, is_auto FROM backups 
                WHERE creator_id = ? OR guild_id = ?
                ORDER BY created_at DESC LIMIT 20
            """, (ctx.author.id, ctx.guild.id)) as cursor:
                backups = await cursor.fetchall()

        if not backups:
            return await ctx.send("<:icon_cross:1372375094336425986> No backups found for you or this server.")

        embed = discord.Embed(
            title="📦 𝐘𝐨𝐮𝐫 𝐒𝐞𝐫𝐯𝐞𝐫 𝐁𝐚𝐜𝐤𝐮𝐩𝐬",
            color=0x000000,
            description="*Here are your saved 24/7 server backups:*"
        )
        lines = []
        for b_id, g_name, c_at, is_auto in backups:
            auto_tag = " `[24/7 AUTO]`" if is_auto else ""
            try:
                date_str = datetime.fromisoformat(c_at).strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = str(c_at)[:16]
            lines.append(f"🔹 **`{b_id}`**{auto_tag} — **{g_name}**\n   📅 *Created: {date_str} UTC*")

        embed.add_field(name="💾 Available Backups", value="\n\n".join(lines), inline=False)
        embed.set_footer(text="💡 Use '&backup info <id>' or '&backup load <id>'")
        await ctx.send(embed=embed)

    @backup.command(name="info", aliases=['show', 'view'], description="View details of a server backup")
    async def info(self, ctx, backup_id: str):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT backup_id, guild_name, creator_id, created_at, roles, categories, channels, emojis, is_auto FROM backups WHERE backup_id = ?", (backup_id,)) as cursor:
                backup = await cursor.fetchone()

        if not backup:
            return await ctx.send("<:icon_cross:1372375094336425986> Backup not found.")

        b_id, g_name, c_id, c_at, roles_raw, cats_raw, chans_raw, emos_raw, is_auto = backup
        roles = json.loads(roles_raw or "[]")
        categories = json.loads(cats_raw or "[]")
        channels = json.loads(chans_raw or "[]")
        emojis = json.loads(emos_raw or "[]")

        embed = discord.Embed(
            title="📋 𝐁𝐚𝐜𝐤𝐮𝐩 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧",
            color=0x000000,
            description=f"**Backup ID:** `{b_id}`{' `[24/7 AUTO]`' if is_auto else ''}"
        )
        embed.add_field(
            name="🏠 Server Details",
            value=f"**Name:** {g_name}\n**Creator:** <@{c_id}>\n**Created:** {c_at[:19]} UTC",
            inline=False
        )
        embed.add_field(name="🎭 Roles", value=f"**{len(roles)}** roles", inline=True)
        embed.add_field(name="📁 Categories", value=f"**{len(categories)}** categories", inline=True)
        embed.add_field(name="📺 Channels", value=f"**{len(channels)}** channels", inline=True)
        embed.add_field(name="😀 Emojis", value=f"**{len(emojis)}** emojis", inline=True)
        embed.add_field(name="🔒 Status", value="✅ Ready 24/7", inline=True)
        embed.set_footer(text=f"💡 Use '&backup load {b_id}' to restore this backup")
        await ctx.send(embed=embed)

    @backup.command(name="delete", aliases=['del', 'rm'], description="Delete a server backup")
    async def delete(self, ctx, backup_id: str):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT creator_id FROM backups WHERE backup_id = ?", (backup_id,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return await ctx.send("<:icon_cross:1372375094336425986> Backup not found.")
            if not (self.is_owner(ctx.author.id) or row[0] == ctx.author.id):
                return await ctx.send("<:icon_cross:1372375094336425986> You can only delete your own backups.")

            await db.execute("DELETE FROM backups WHERE backup_id = ?", (backup_id,))
            await db.commit()

        embed = discord.Embed(
            title="🗑️ Backup Deleted Successfully",
            color=0x000000,
            description=f"**Backup ID:** `{backup_id}` has been permanently deleted from storage."
        )
        await ctx.send(embed=embed)

    @backup.command(name="export", aliases=['dl', 'download'], description="Export a server backup as a JSON file")
    async def export(self, ctx, backup_id: str):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT backup_id, guild_id, guild_name, creator_id, created_at, roles, categories, channels, emojis FROM backups WHERE backup_id = ?", (backup_id,)) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("<:icon_cross:1372375094336425986> Backup not found.")

        data = {
            "backup_id": row[0],
            "guild_id": row[1],
            "guild_name": row[2],
            "creator_id": row[3],
            "created_at": row[4],
            "roles": json.loads(row[5] or "[]"),
            "categories": json.loads(row[6] or "[]"),
            "channels": json.loads(row[7] or "[]"),
            "emojis": json.loads(row[8] or "[]")
        }
        encoded = json.dumps(data, indent=2, default=str).encode('utf-8')
        file = discord.File(io.BytesIO(encoded), filename=f"backup_{backup_id}.json")
        embed = discord.Embed(
            title="📤 Backup Exported Successfully",
            color=0x000000,
            description=f"**Backup ID:** `{backup_id}` exported as JSON file."
        )
        await ctx.send(embed=embed, file=file)

    @backup.command(name="import", aliases=['upload'], description="Import a server backup from a JSON file")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def import_backup(self, ctx):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")
        if not ctx.message.attachments:
            return await ctx.send("<:icon_cross:1372375094336425986> Please attach a valid JSON backup file.")

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".json"):
            return await ctx.send("<:icon_cross:1372375094336425986> Attached file must be a `.json` file.")

        try:
            content = await attachment.read()
            data = json.loads(content)
            for req in ["guild_name", "roles", "categories", "channels", "emojis"]:
                if req not in data:
                    return await ctx.send(f"<:icon_cross:1372375094336425986> Invalid backup file: missing `{req}` field.")

            new_id = generate_backup_id()
            now_iso = datetime.utcnow().isoformat()
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    INSERT INTO backups (backup_id, guild_id, guild_name, creator_id, created_at, roles, categories, channels, emojis, is_auto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    new_id, data.get("guild_id", ctx.guild.id), data["guild_name"],
                    ctx.author.id, now_iso, json.dumps(data["roles"]), json.dumps(data["categories"]),
                    json.dumps(data["channels"]), json.dumps(data["emojis"])
                ))
                await db.commit()

            embed = discord.Embed(
                title="📥 Backup Imported Successfully",
                color=0x000000,
                description=f"**New Backup ID:** `{new_id}`\n\n🎭 Roles: {len(data['roles'])}\n📺 Channels: {len(data['channels'])}\n😀 Emojis: {len(data['emojis'])}"
            )
            embed.set_footer(text=f"Restore with: &backup load {new_id}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"<:icon_cross:1372375094336425986> Error importing backup: {e}")

    @backup.command(name="load", aliases=['restore', 'apply'], description="Restore a server backup by ID")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def load(self, ctx, backup_id: str):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT backup_id, guild_name, roles, categories, channels, emojis FROM backups WHERE backup_id = ?", (backup_id,)) as cursor:
                backup_row = await cursor.fetchone()

        if not backup_row:
            return await ctx.send("<:icon_cross:1372375094336425986> Backup not found.")

        b_id, g_name, roles_raw, cats_raw, chans_raw, emos_raw = backup_row
        backup = {
            "backup_id": b_id,
            "guild_name": g_name,
            "roles": json.loads(roles_raw or "[]"),
            "categories": json.loads(cats_raw or "[]"),
            "channels": json.loads(chans_raw or "[]"),
            "emojis": json.loads(emos_raw or "[]")
        }

        class ConfirmView(View):
            def __init__(self):
                super().__init__(timeout=180)
                self.selection = None
                self.timed_out = False
                select = Select(
                    placeholder="Select what to replace/restore",
                    min_values=1,
                    max_values=5,
                    options=[
                        discord.SelectOption(label="Roles", value="roles", emoji="🧷"),
                        discord.SelectOption(label="Channels", value="channels", emoji="📺"),
                        discord.SelectOption(label="Categories", value="categories", emoji="🗂️"),
                        discord.SelectOption(label="Emojis", value="emojis", emoji="🙂"),
                        discord.SelectOption(label="All Structure", value="all", emoji="🗃️"),
                    ]
                )
                select.callback = self.select_callback
                self.add_item(select)
                confirm_btn = Button(label="Confirm Restore", style=discord.ButtonStyle.green)
                confirm_btn.callback = self.confirm_callback
                self.add_item(confirm_btn)
                cancel_btn = Button(label="Cancel", style=discord.ButtonStyle.red)
                cancel_btn.callback = self.cancel_callback
                self.add_item(cancel_btn)

            async def select_callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Only the command author can select.", ephemeral=True)
                await interaction.response.defer(ephemeral=True)
                self.selection = interaction.data["values"]
                await interaction.followup.send(f"Selected: {', '.join(self.selection)}. Click Confirm Restore.", ephemeral=True)

            async def confirm_callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Only the command author can confirm.", ephemeral=True)
                await interaction.response.defer(ephemeral=True)
                self.stop()

            async def cancel_callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Only the command author can cancel.", ephemeral=True)
                await interaction.response.send_message("Backup restoration cancelled.", ephemeral=True)
                self.selection = None
                self.stop()

            async def on_timeout(self):
                self.timed_out = True
                for item in self.children:
                    item.disabled = True

        view = ConfirmView()
        await ctx.send("Select which server components to restore:", view=view)
        await view.wait()

        if not view.selection:
            return await ctx.send("Restoration cancelled or timed out.")

        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("<:icon_cross:1372375094336425986> Bot lacks `Manage Channels` permission.")

        status = discord.utils.get(ctx.guild.channels, name="backup-status")
        if not status:
            try:
                status = await ctx.guild.create_text_channel("backup-status")
            except Exception as e:
                return await ctx.send(f"Failed to create status channel: {e}")

        await self.post_status(status, "🧹 Deleting selected existing components...")
        try:
            if "all" in view.selection or "channels" in view.selection:
                for ch in ctx.guild.channels:
                    if ch.id != status.id:
                        await self.safe_delete(ch, status)
            if "all" in view.selection or "roles" in view.selection:
                for r in ctx.guild.roles:
                    if not r.is_default() and not r.managed:
                        await self.safe_delete(r, status)
            if "all" in view.selection or "emojis" in view.selection:
                for e in ctx.guild.emojis:
                    await self.safe_delete(e, status)
            if "all" in view.selection or "categories" in view.selection:
                for cat in ctx.guild.categories:
                    await self.safe_delete(cat, status)
        except Exception as e:
            await self.post_status(status, f"Error deleting: {e}")

        # Restore Roles
        old_to_new_role = {}
        if "all" in view.selection or "roles" in view.selection:
            await self.post_status(status, "🎭 Restoring roles...")
            bot_member = ctx.guild.get_member(self.bot.user.id)
            bot_top_pos = bot_member.top_role.position if bot_member else 1

            for r in sorted(backup["roles"], key=lambda x: x.get("position", 1), reverse=False):
                try:
                    new_role = await ctx.guild.create_role(
                        name=r["name"],
                        colour=discord.Colour(r["color"]),
                        hoist=r["hoist"],
                        mentionable=r["mentionable"]
                    )
                    old_to_new_role[r["id"]] = new_role
                    await asyncio.sleep(0.4)
                except Exception as e:
                    logger.warning(f"Error creating role {r.get('name')}: {e}")

        # Restore Categories
        category_map = {}
        if "all" in view.selection or "categories" in view.selection:
            await self.post_status(status, "🗂️ Restoring categories...")
            for cat_data in sorted(backup["categories"], key=lambda x: x.get("position", 0)):
                try:
                    cat = await ctx.guild.create_category(cat_data["name"])
                    category_map[cat_data["name"]] = cat
                    await asyncio.sleep(0.4)
                except Exception as e:
                    logger.warning(f"Error creating category {cat_data.get('name')}: {e}")

        # Restore Channels
        if "all" in view.selection or "channels" in view.selection:
            await self.post_status(status, "📺 Restoring channels...")
            for ch_data in backup["channels"]:
                try:
                    cat = category_map.get(ch_data.get("category"))
                    overwrites = {}
                    for perm in ch_data.get("overwrites", []):
                        target_id = perm["id"]
                        target = old_to_new_role.get(target_id) if perm["type"] == "role" else ctx.guild.get_member(target_id)
                        if target:
                            overwrites[target] = discord.PermissionOverwrite.from_pair(
                                discord.Permissions(perm["allow"]),
                                discord.Permissions(perm["deny"])
                            )

                    ch_name = ch_data["name"][:100]
                    if ch_data["type"] == "text":
                        await ctx.guild.create_text_channel(
                            name=ch_name,
                            topic=ch_data.get("topic"),
                            slowmode_delay=ch_data.get("slowmode", 0),
                            nsfw=ch_data.get("nsfw", False),
                            category=cat,
                            overwrites=overwrites
                        )
                    elif ch_data["type"] == "voice":
                        await ctx.guild.create_voice_channel(
                            name=ch_name,
                            bitrate=min(ch_data.get("bitrate", 64000), 96000),
                            user_limit=ch_data.get("user_limit", 0),
                            category=cat,
                            overwrites=overwrites
                        )
                    await asyncio.sleep(0.4)
                except Exception as e:
                    logger.warning(f"Error creating channel {ch_data.get('name')}: {e}")

        # Restore Emojis
        if "all" in view.selection or "emojis" in view.selection:
            await self.post_status(status, "🙂 Restoring emojis...")
            for e_data in backup["emojis"][:50]:
                try:
                    async with self.session.get(e_data["url"]) as resp:
                        if resp.status == 200:
                            img = await resp.read()
                            await self.create_emoji_with_retry(ctx.guild, e_data["name"], img, status)
                except Exception as e:
                    logger.warning(f"Error restoring emoji {e_data.get('name')}: {e}")

        await self.post_status(status, "🎉 **24/7 Backup restoration completed successfully!**", color=0x000000)

async def setup(bot):
    await bot.add_cog(Backup(bot))
