import discord
from discord.ext import commands, tasks
import aiosqlite
import os
import json
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "db/premium.db"
OWNER_IDS = [1542661619245383683, 1542645079993483266, 1124248109472550993]

async def is_premium_guild(guild_id: int) -> bool:
    """Check if a guild has active premium status"""
    if not guild_id:
        return False
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_premium (
                guild_id INTEGER PRIMARY KEY,
                guild_name TEXT,
                tier TEXT DEFAULT 'Lifetime Diamond',
                granted_by INTEGER,
                granted_at TEXT,
                expires_at TEXT
            )
        """)
        await db.commit()
        async with db.execute("SELECT expires_at FROM server_premium WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            expires_at = row[0]
            if expires_at is None:
                return True
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                return exp_dt > datetime.utcnow()
            except Exception:
                return True

class Premium(commands.Cog):
    """Exclusive Server Premium System granted by Bot Owners"""
    def __init__(self, bot):
        self.bot = bot
        self.expiry_loop.start()
        bot.loop.create_task(self.init_db())

    async def init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_premium (
                    guild_id INTEGER PRIMARY KEY,
                    guild_name TEXT,
                    tier TEXT DEFAULT 'Lifetime Diamond',
                    granted_by INTEGER,
                    granted_at TEXT,
                    expires_at TEXT
                )
            """)
            await db.commit()

        # Automatically pre-grant Lifetime Diamond to the owner's primary servers
        await self.bot.wait_until_ready()
        now_iso = datetime.utcnow().isoformat()
        for guild in self.bot.guilds:
            if guild.owner_id in OWNER_IDS or guild.id == 1553456580534599806:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("""
                        INSERT OR IGNORE INTO server_premium (guild_id, guild_name, tier, granted_by, granted_at, expires_at)
                        VALUES (?, ?, 'Lifetime Diamond', ?, ?, NULL)
                    """, (guild.id, guild.name, guild.owner_id or OWNER_IDS[0], now_iso))
                    await db.commit()

    async def cog_unload(self):
        self.expiry_loop.cancel()

    def is_owner(self, user_id: int) -> bool:
        owner_env = os.getenv("OWNER_IDS", "")
        env_owner_ids = [int(i.strip()) for i in owner_env.split(",") if i.strip().isdigit()]
        return user_id in OWNER_IDS or user_id in env_owner_ids

    @tasks.loop(minutes=30)
    async def expiry_loop(self):
        """Check and clean up expired premium subscriptions"""
        await self.bot.wait_until_ready()
        try:
            now_iso = datetime.utcnow().isoformat()
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    DELETE FROM server_premium 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (now_iso,))
                await db.commit()
        except Exception as e:
            pass

    @expiry_loop.before_loop
    async def before_expiry_loop(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_group(
        name="premium",
        aliases=['prem', 'serverpremium', 'donator'],
        description="View or manage server premium features",
        invoke_without_command=True
    )
    async def premium(self, ctx):
        if not ctx.guild:
            return await ctx.send("This command must be used in a server.")

        is_prem = await is_premium_guild(ctx.guild.id)
        if is_prem:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT tier, granted_by, granted_at, expires_at FROM server_premium WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                    row = await cursor.fetchone()

            tier = row[0] if row else "Lifetime Diamond"
            granter_id = row[1] if row else OWNER_IDS[0]
            granted_at = row[2][:10] if row and row[2] else "Active"
            expires_at = row[3] if row and row[3] else "Never (Permanent Lifetime)"

            embed = discord.Embed(
                title="💎 ✦ 𝐒𝐓𝐑𝐄𝐋𝐈𝐙𝐈𝐀 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 ✦ 💎",
                description=f"### 👑 Server Status: **ACTIVE**\n**{ctx.guild.name}** is enjoying all exclusive VIP perks!\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=0x00FFFF
            )
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)

            embed.add_field(name="🏆 **Tier**", value=f"`{tier}`", inline=True)
            embed.add_field(name="👑 **Granted By**", value=f"<@{granter_id}>", inline=True)
            embed.add_field(name="⏳ **Expiration**", value=f"**{expires_at}**", inline=True)

            embed.add_field(
                name="✨ **Active Server Perks**",
                value=(
                    "💎 **24/7 Voice Channel Stay** — Bot never disconnects\n"
                    "🛡️ **24/7 Automated Backups** — Continuous server protection\n"
                    "⚡ **Server-Wide No-Prefix** — Prefixless commands for all members\n"
                    "🎨 **Full Server Customization** — Custom banner, color & nickname\n"
                    "🔊 **Enhanced Audio Stream** — Highest quality, high bitrate audio\n"
                    "🚀 **Priority Gateway** — Instant response & zero rate limits"
                ),
                inline=False
            )
            embed.set_footer(text=f"Server ID: {ctx.guild.id} • Premium Tier Active")
            embed.timestamp = datetime.utcnow()
            return await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="💎 ✦ 𝐒𝐓𝐑𝐄𝐋𝐈𝐙𝐈𝐀 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 ✦ 💎",
                description=f"### 🔒 Server Status: **INACTIVE**\n**{ctx.guild.name}** does not currently have active Premium.\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=0x000000
            )
            embed.add_field(
                name="🌟 **Unlock Exclusive Perks**",
                value=(
                    "💎 **24/7 Voice Channel Stay**\n"
                    "🛡️ **24/7 Automated Cloud Backups**\n"
                    "⚡ **Server-Wide No-Prefix Mode**\n"
                    "🎨 **Full Server Tailoring & Customization**\n"
                    "🔊 **Ultra High Quality Audio**\n"
                    "🚀 **VIP Anti-Nuke & Moderation Bypass**"
                ),
                inline=False
            )
            embed.add_field(
                name="👑 **How to get Premium?**",
                value="Contact the Bot Owner or run `&premium grant` if authorized.",
                inline=False
            )
            return await ctx.send(embed=embed)

    @premium.command(name="grant", aliases=['add', 'activate'], description="Grant premium status to a server (Bot Owner only)")
    async def grant(self, ctx, target_guild: Optional[str] = None, duration: str = "lifetime"):
        """Grant premium status to a server. Usage: &premium grant [guild_id] [duration]"""
        if not self.is_owner(ctx.author.id):
            return await ctx.send("<:icon_cross:1372375094336425986> Only the bot owner can grant server premium.")

        # Resolve target guild
        target_id = None
        target_name = "Unknown Guild"
        if target_guild is None:
            if ctx.guild:
                target_id = ctx.guild.id
                target_name = ctx.guild.name
            else:
                return await ctx.send("<:icon_cross:1372375094336425986> Specify a guild ID.")
        else:
            # Check if duration was passed as first arg (e.g. &premium grant lifetime)
            if target_guild.lower() in ['lifetime', '1w', '2w', '1m', '3m', '6m', '1y', 'perm', 'permanent']:
                duration = target_guild
                target_id = ctx.guild.id
                target_name = ctx.guild.name
            elif target_guild.isdigit():
                target_id = int(target_guild)
                g = self.bot.get_guild(target_id)
                target_name = g.name if g else f"Guild ID {target_id}"
            else:
                target_id = ctx.guild.id
                target_name = ctx.guild.name

        # Calculate expiration
        duration_map = {
            "1w": timedelta(weeks=1),
            "2w": timedelta(weeks=2),
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "6m": timedelta(days=180),
            "1y": timedelta(days=365),
            "2y": timedelta(days=730),
        }

        dur_lower = duration.lower()
        exp_iso = None
        exp_display = "Permanent (Lifetime)"
        tier_name = "Lifetime Diamond"

        if dur_lower in duration_map:
            exp_dt = datetime.utcnow() + duration_map[dur_lower]
            exp_iso = exp_dt.isoformat()
            exp_display = exp_dt.strftime("%Y-%m-%d %H:%M UTC")
            tier_name = f"Premium ({dur_lower.upper()})"

        now_iso = datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO server_premium (guild_id, guild_name, tier, granted_by, granted_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    guild_name = excluded.guild_name,
                    tier = excluded.tier,
                    granted_by = excluded.granted_by,
                    granted_at = excluded.granted_at,
                    expires_at = excluded.expires_at
            """, (target_id, target_name, tier_name, ctx.author.id, now_iso, exp_iso))
            await db.commit()

        # Automatically enable server_np in db/np.db for convenience
        try:
            async with aiosqlite.connect("db/np.db") as np_db:
                await np_db.execute("INSERT OR IGNORE INTO server_np (guild_id) VALUES (?)", (target_id,))
                await np_db.commit()
        except Exception:
            pass

        embed = discord.Embed(
            title="💎 ✦ 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐆𝐑𝐀𝐍𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘 ✦ 💎",
            description=(
                f"### 🎉 **{target_name}** is now a **Premium Server**!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👑 **Granted By:** {ctx.author.mention}\n"
                f"🏆 **Tier:** `{tier_name}`\n"
                f"⏳ **Duration:** `{exp_display}`\n"
                f"🆔 **Guild ID:** `{target_id}`\n\n"
                f"✨ *All VIP perks (24/7 VC, Auto-Backups, No-Prefix, Customization) have been fully unlocked.*"
            ),
            color=0x00FFFF
        )
        if ctx.guild and ctx.guild.id == target_id and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="D4Hz VIP Network • Thank you for your support!")
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @premium.command(name="revoke", aliases=['remove', 'cancel'], description="Revoke premium status from a server (Bot Owner only)")
    async def revoke(self, ctx, target_guild: Optional[str] = None):
        """Revoke premium status from a server"""
        if not self.is_owner(ctx.author.id):
            return await ctx.send("<:icon_cross:1372375094336425986> Only the bot owner can revoke server premium.")

        target_id = int(target_guild) if (target_guild and target_guild.isdigit()) else (ctx.guild.id if ctx.guild else None)
        if not target_id:
            return await ctx.send("<:icon_cross:1372375094336425986> Specify a guild ID.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT guild_name FROM server_premium WHERE guild_id = ?", (target_id,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return await ctx.send(f"<:icon_cross:1372375094336425986> Guild `{target_id}` does not have active premium.")

            guild_name = row[0]
            await db.execute("DELETE FROM server_premium WHERE guild_id = ?", (target_id,))
            await db.commit()

        embed = discord.Embed(
            title="🔴 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐑𝐞𝐯𝐨𝐤𝐞𝐝",
            description=f"Premium access has been revoked from **{guild_name}** (`{target_id}`).",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @premium.command(name="list", aliases=['all', 'servers'], description="List all premium servers (Bot Owner only)")
    async def list_premium(self, ctx):
        """List all servers with active premium"""
        if not self.is_owner(ctx.author.id):
            return await ctx.send("<:icon_cross:1372375094336425986> Only the bot owner can view the full premium list.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT guild_id, guild_name, tier, expires_at FROM server_premium ORDER BY guild_name ASC") as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await ctx.send("No servers currently have active premium.")

        lines = []
        for g_id, g_name, tier, exp in rows:
            exp_str = exp[:10] if exp else "Lifetime"
            lines.append(f"💎 **{g_name}** (`{g_id}`)\n   └ Tier: `{tier}` • Expires: `{exp_str}`")

        embed = discord.Embed(
            title=f"💎 ✦ 𝐀𝐜𝐭𝐢𝐯𝐞 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐒𝐞𝐫𝐯𝐞𝐫𝐬 [{len(rows)}] ✦",
            description="\n\n".join(lines),
            color=0x00FFFF
        )
        await ctx.send(embed=embed)

    @premium.command(name="perks", aliases=['features'], description="View all exclusive server premium perks")
    async def perks(self, ctx):
        """Display the complete list of premium perks"""
        embed = discord.Embed(
            title="💎 ✦ 𝐒𝐓𝐑𝐄𝐋𝐈𝐙𝐈𝐀 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐏𝐄𝐑𝐊𝐒 ✦ 💎",
            description="Here are all the elite features unlocked with Server Premium:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x00FFFF
        )
        embed.add_field(
            name="🔊 𝟐𝟒/𝟕 𝐕𝐨𝐢𝐜𝐞 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐒𝐭𝐚𝐲",
            value="The bot stays permanently inside your server's voice channel 24/7 without ever leaving.",
            inline=False
        )
        embed.add_field(
            name="🛡️ 𝟐𝟒/𝟕 𝐀𝐮𝐭𝐨𝐦𝐚𝐭𝐞𝐝 𝐂𝐥𝐨𝐮𝐝 𝐁𝐚𝐜𝐤𝐮𝐩𝐬",
            value="Automated server snapshots taken every 12-24 hours so your server structure is always protected.",
            inline=False
        )
        embed.add_field(
            name="⚡ 𝐒𝐞𝐫𝐯𝐞𝐫-𝐖𝐢𝐝𝐞 𝐍𝐨-𝐏𝐫𝐞𝐟𝐢𝐱",
            value="All server members can use commands instantly without typing `&` (e.g. just type `help`, `play`, `skip`).",
            inline=False
        )
        embed.add_field(
            name="🎨 𝐅𝐮𝐥𝐥 𝐒𝐞𝐫𝐯𝐞𝐫 𝐂𝐮𝐬𝐭𝐨𝐦𝐢𝐳𝐚𝐭𝐢𝐨𝐧",
            value="Tailor the bot with custom prefixes, custom bot nicknames, custom embed colors, and banners.",
            inline=False
        )
        embed.add_field(
            name="💎 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐕𝐈𝐏 𝐁𝐚𝐝𝐠𝐞",
            value="Special Diamond badges displayed on dashboard and server status cards.",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Premium(bot))
