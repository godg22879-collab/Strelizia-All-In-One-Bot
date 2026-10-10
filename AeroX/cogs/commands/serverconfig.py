import discord
from discord.ext import commands
import aiosqlite
import os
import json
from datetime import datetime
from utils.Tools import getConfig, updateConfig

DB_PATH = "db/server_config.db"
OWNER_IDS = [1542661619245383683, 1542645079993483266, 1124248109472550993]

async def get_server_customization(guild_id: int):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_customization (
                guild_id INTEGER PRIMARY KEY,
                embed_color INTEGER DEFAULT NULL,
                banner_url TEXT DEFAULT NULL,
                custom_greeting TEXT DEFAULT NULL
            )
        """)
        await db.commit()
        async with db.execute("SELECT embed_color, banner_url, custom_greeting FROM server_customization WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "embed_color": row[0],
                    "banner_url": row[1],
                    "custom_greeting": row[2]
                }
    return {"embed_color": None, "banner_url": None, "custom_greeting": None}

class ServerConfig(commands.Cog):
    """Server-Specific Customization and Configuration System"""
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.init_db())

    async def init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_customization (
                    guild_id INTEGER PRIMARY KEY,
                    embed_color INTEGER DEFAULT NULL,
                    banner_url TEXT DEFAULT NULL,
                    custom_greeting TEXT DEFAULT NULL
                )
            """)
            await db.commit()

    def is_admin(self, ctx):
        if not ctx.guild:
            return False
        if ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner:
            return True
        return ctx.author.id in OWNER_IDS

    @commands.command(name="serverprefix", aliases=['sp', 'guildprefix', 'botprefix'], description="Set a custom prefix for this server.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_prefix(self, ctx, new_prefix: str = None):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        if not new_prefix:
            cfg = await getConfig(ctx.guild.id)
            curr = cfg.get("prefix", "&")
            embed = discord.Embed(
                title="📌 𝐒𝐞𝐫𝐯𝐞𝐫 𝐏𝐫𝐞𝐟𝐢𝐱",
                description=f"Current prefix for **{ctx.guild.name}** is: `{curr}`\n\n💡 *Change it with `&setprefix <new_prefix>`*",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        if len(new_prefix) > 5:
            return await ctx.send("<:icon_cross:1372375094336425986> Prefix cannot exceed 5 characters.")

        await updateConfig(ctx.guild.id, {"prefix": new_prefix})
        embed = discord.Embed(
            title="✅ 𝐏𝐫𝐞𝐟𝐢𝐱 𝐔𝐩𝐝𝐚𝐭𝐞𝐝",
            description=f"Successfully set server prefix to: `{new_prefix}`\nExample: `{new_prefix}help`",
            color=0x000000
        )
        await ctx.send(embed=embed)

    @commands.command(name="botnick", aliases=['setbotnick', 'changenick', 'editnick'], description="Change the bot's nickname in this server.")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def set_nickname(self, ctx, *, nickname: str = None):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        bot_member = ctx.guild.me
        if not bot_member.guild_permissions.change_nickname and not bot_member.guild_permissions.manage_nicknames:
            return await ctx.send("<:icon_cross:1372375094336425986> Bot lacks `Change Nickname` permission.")

        if nickname is None or nickname.lower() in ['reset', 'none', 'clear', 'default']:
            try:
                await bot_member.edit(nick=None)
                embed = discord.Embed(
                    title="🤖 𝐍𝐢𝐜𝐤𝐧𝐚𝐦𝐞 𝐑𝐞𝐬𝐞𝐭",
                    description=f"Bot nickname reset to default (**{self.bot.user.name}**).",
                    color=0x000000
                )
                return await ctx.send(embed=embed)
            except Exception as e:
                return await ctx.send(f"<:icon_cross:1372375094336425986> Failed to reset nickname: {e}")

        if len(nickname) > 32:
            return await ctx.send("<:icon_cross:1372375094336425986> Nickname must be 32 characters or fewer.")

        try:
            await bot_member.edit(nick=nickname)
            embed = discord.Embed(
                title="🤖 𝐍𝐢𝐜𝐤𝐧𝐚𝐦𝐞 𝐔𝐩𝐝𝐚𝐭𝐞𝐝",
                description=f"Bot nickname in **{ctx.guild.name}** is now **{nickname}**.",
                color=0x000000
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"<:icon_cross:1372375094336425986> Could not change nickname: {e}")

    @commands.command(name="setcolor", aliases=['setcolour', 'embedcolor', 'servercolor', 'botcolor'], description="Set custom embed color theme for this server.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_color(self, ctx, hex_code: str = None):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        if not hex_code:
            data = await get_server_customization(ctx.guild.id)
            curr = data.get("embed_color")
            c_str = f"#{curr:06x}" if curr is not None else "Default (0x000000 Black)"
            embed = discord.Embed(
                title="🎨 𝐒𝐞𝐫𝐯𝐞𝐫 𝐄𝐦𝐛𝐞𝐝 𝐂𝐨𝐥𝐨𝐫",
                description=f"Current theme color: `{c_str}`\n\n💡 *Change it with `&setcolor #ff0055` or `&setcolor reset`*",
                color=curr if curr is not None else 0x000000
            )
            return await ctx.send(embed=embed)

        if hex_code.lower() in ['reset', 'default', 'none']:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE server_customization SET embed_color = NULL WHERE guild_id = ?", (ctx.guild.id,))
                await db.commit()
            return await ctx.send("✅ Embed color reset to default.")

        clean_hex = hex_code.strip().replace("#", "").replace("0x", "")
        try:
            color_int = int(clean_hex, 16)
            if color_int < 0 or color_int > 0xFFFFFF:
                raise ValueError()
        except ValueError:
            return await ctx.send("<:icon_cross:1372375094336425986> Invalid hex color. Examples: `#5865F2`, `#FF0055`, `0x2ECC71`")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO server_customization (guild_id, embed_color)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET embed_color = excluded.embed_color
            """, (ctx.guild.id, color_int))
            await db.commit()

        embed = discord.Embed(
            title="🎨 𝐓𝐡𝐞𝐦𝐞 𝐂𝐨𝐥𝐨𝐫 𝐔𝐩𝐝𝐚𝐭𝐞𝐝",
            description=f"Server embed color updated to **#{color_int:06X}**!",
            color=color_int
        )
        await ctx.send(embed=embed)

    @commands.command(name="setbanner", aliases=['serverbanner', 'botbanner'], description="Set custom banner image for server embeds.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_banner(self, ctx, url: str = None):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        if not url:
            data = await get_server_customization(ctx.guild.id)
            curr = data.get("banner_url")
            embed = discord.Embed(
                title="🖼️ 𝐒𝐞𝐫𝐯𝐞𝐫 𝐁𝐚𝐧𝐧𝐞𝐫",
                description=f"Current banner: {f'[View Banner]({curr})' if curr else 'Default (D4Hz.gif)'}\n\n💡 *Set with `&setbanner <image_url>` or `&setbanner reset`*",
                color=0x000000
            )
            if curr:
                embed.set_image(url=curr)
            return await ctx.send(embed=embed)

        if url.lower() in ['reset', 'default', 'none']:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE server_customization SET banner_url = NULL WHERE guild_id = ?", (ctx.guild.id,))
                await db.commit()
            return await ctx.send("✅ Banner reset to default.")

        if not (url.startswith("http://") or url.startswith("https://")):
            return await ctx.send("<:icon_cross:1372375094336425986> Please provide a valid HTTP/HTTPS image URL.")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO server_customization (guild_id, banner_url)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET banner_url = excluded.banner_url
            """, (ctx.guild.id, url))
            await db.commit()

        embed = discord.Embed(
            title="🖼️ 𝐁𝐚𝐧𝐧𝐞𝐫 𝐔𝐩𝐝𝐚𝐭𝐞𝐝",
            description=f"Server banner successfully updated!\n[Image Link]({url})",
            color=0x000000
        )
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="serverconfig", aliases=['serversettings', 'botconfig', 'customization', 'sc'], description="Show full server customization dashboard.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def server_config_dashboard(self, ctx):
        if not ctx.guild:
            return await ctx.send("This command must be used in a server.")

        # 1. Prefix
        cfg = await getConfig(ctx.guild.id)
        prefix = cfg.get("prefix", "&")

        # 2. Nickname
        bot_member = ctx.guild.me
        nick = bot_member.nick if bot_member.nick else f"{self.bot.user.name} *(Default)*"

        # 3. Customization
        custom = await get_server_customization(ctx.guild.id)
        color_val = custom.get("embed_color")
        color_str = f"#{color_val:06X}" if color_val is not None else "Default (0x000000)"
        banner_url = custom.get("banner_url")

        # 4. Server No-Prefix
        is_server_np = False
        try:
            async with aiosqlite.connect("db/np.db") as db:
                async with db.execute("SELECT guild_id FROM server_np WHERE guild_id = ?", (ctx.guild.id,)) as c:
                    if await c.fetchone():
                        is_server_np = True
        except Exception:
            pass

        # 5. 24/7 VC
        twenty_four_seven_file = "jsondb/247_channels.json"
        vc_247_str = "None (Disabled)"
        if os.path.exists(twenty_four_seven_file):
            try:
                with open(twenty_four_seven_file, 'r') as f:
                    data = json.load(f)
                    ch_id = data.get(str(ctx.guild.id))
                    if ch_id:
                        ch = ctx.guild.get_channel(int(ch_id))
                        vc_247_str = f"🟢 {ch.mention} (`{ch_id}`)" if ch else f"🟢 `<#{ch_id}>`"
            except Exception:
                pass

        # 6. Auto-Backup
        auto_bk_str = "🔴 Disabled"
        try:
            async with aiosqlite.connect("db/backups.db") as db:
                async with db.execute("SELECT enabled, interval_hours FROM auto_backup_settings WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] == 1:
                        auto_bk_str = f"🟢 Active (Every {row[1]}h)"
        except Exception:
            pass

        # 7. Premium
        prem_str = "🔴 Inactive"
        try:
            async with aiosqlite.connect("db/premium.db") as db:
                async with db.execute("SELECT tier FROM server_premium WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                    p_row = await cursor.fetchone()
                    if p_row:
                        prem_str = f"💎 **{p_row[0]}**"
        except Exception:
            pass

        embed = discord.Embed(
            title=f"⚙️ 𝐒𝐞𝐫𝐯𝐞𝐫 𝐂𝐮𝐬𝐭𝐨𝐦𝐢𝐳𝐚𝐭𝐢𝐨𝐧 𝐃𝐚𝐬𝐡𝐛𝐨𝐚𝐫𝐝",
            description=f"Custom configurations tailored for **{ctx.guild.name}**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=color_val if color_val is not None else 0x000000
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.add_field(name="📌 **Server Prefix**", value=f"`{prefix}`\n*Cmd: `&setprefix <prefix>`*", inline=True)
        embed.add_field(name="🤖 **Bot Nickname**", value=f"**{nick}**\n*Cmd: `&setnick <nick>`*", inline=True)
        embed.add_field(name="🎨 **Theme Color**", value=f"`{color_str}`\n*Cmd: `&setcolor <hex>`*", inline=True)

        embed.add_field(
            name="⚡ **Server No-Prefix**",
            value=f"{'🟢 **Enabled (Prefix-less)**' if is_server_np else '🔴 **Disabled (Prefix Required)**'}\n*Cmd: `&servernp on/off`*",
            inline=True
        )
        embed.add_field(name="🔊 **24/7 Voice Channel**", value=f"{vc_247_str}\n*Cmd: `&stay` or `&247 on`*", inline=True)
        embed.add_field(name="🕒 **24/7 Auto-Backup**", value=f"{auto_bk_str}\n*Cmd: `&backup auto on`*", inline=True)
        embed.add_field(name="💎 **Server Premium**", value=f"{prem_str}\n*Cmd: `&premium`*", inline=True)

        if banner_url:
            embed.set_image(url=banner_url)

        embed.set_footer(text=f"Server ID: {ctx.guild.id} • Use &resetconfig to reset all")
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.command(name="resetconfig", aliases=['resetcustomization'], description="Reset all server customizations to default.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def reset_config(self, ctx):
        if not self.is_admin(ctx):
            return await ctx.send("<:icon_cross:1372375094336425986> Administrator permissions required.")

        # Reset prefix
        await updateConfig(ctx.guild.id, {"prefix": "&"})

        # Reset customization DB
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM server_customization WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        # Reset server_np
        async with aiosqlite.connect("db/np.db") as db:
            await db.execute("DELETE FROM server_np WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        # Reset nick
        try:
            if ctx.guild.me.guild_permissions.change_nickname:
                await ctx.guild.me.edit(nick=None)
        except Exception:
            pass

        embed = discord.Embed(
            title="🔄 𝐒𝐞𝐫𝐯𝐞𝐫 𝐂𝐮𝐬𝐭𝐨𝐦𝐢𝐳𝐚𝐭𝐢𝐨𝐧𝐬 𝐑𝐞𝐬𝐞𝐭",
            description=f"All customizations for **{ctx.guild.name}** have been restored to defaults.",
            color=0x000000
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerConfig(bot))
