import os
import discord
from discord.ext import commands
import aiosqlite
from utils.config import OWNER_IDS
from utils.Tools import *

ACTIONS_MAP = {
    'ban': 'Member Ban',
    'kick': 'Member Kick',
    'memup': 'Timeout & Member Update',
    'voicemod': 'Voice Mute & Deafen',
    'chcr': 'Channel Create',
    'chdl': 'Channel Delete',
    'chup': 'Channel Update',
    'rlcr': 'Role Create',
    'rldl': 'Role Delete',
    'rlup': 'Role Update',
    'meneve': 'Everyone & Mass Mention',
    'mngweb': 'Webhooks Management',
    'mngstemo': 'Emojis & Stickers',
    'serverup': 'Server Settings & Vanity',
    'all': 'Full Antinuke Bypass'
}

class BypassRoles(commands.Cog):
    """Commands for managing Antinuke Bypassing Roles"""
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        async with aiosqlite.connect('db/anti.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bypass_roles (
                    guild_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS action_bypass_roles (
                    guild_id INTEGER,
                    action_type TEXT,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, action_type, role_id)
                )
            ''')
            await db.commit()

    async def is_owner_or_extraowner(self, ctx):
        owner_env = os.getenv("OWNER_IDS", "")
        env_owner_ids = [int(i.strip()) for i in owner_env.split(",") if i.strip().isdigit()]
        if ctx.author.id in OWNER_IDS or ctx.author.id in env_owner_ids or (hasattr(self.bot, 'owner_ids') and self.bot.owner_ids and ctx.author.id in self.bot.owner_ids) or await self.bot.is_owner(ctx.author):
            return True
        if ctx.author.id == ctx.guild.owner_id:
            return True
        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?", (ctx.guild.id, ctx.author.id)) as cursor:
                if await cursor.fetchone():
                    return True
        return False

    @commands.group(name="bypassrole", aliases=["bprole", "bypass"], invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def bypassrole(self, ctx):
        """View available bypass role management commands"""
        prefix = ctx.prefix
        embed = discord.Embed(
            title="🛡️ Antinuke Bypass Roles System",
            description="Bypass roles grant immunity from Antinuke actions to trusted members.",
            color=0x000000
        )
        embed.add_field(
            name="__Commands__",
            value=(
                f"`{prefix}bypassrole create_all` - **Auto-create separate bypass roles for each action!**\n"
                f"`{prefix}bypassrole set <action> <@role>` - Set an action-specific bypass role\n"
                f"`{prefix}bypassrole unset <action> <@role>` - Unset an action bypass role\n"
                f"`{prefix}bypassrole add <@role>` - Add a full bypass role\n"
                f"`{prefix}bypassrole remove <@role>` - Remove a bypass role\n"
                f"`{prefix}bypassrole list` - View all configured bypass roles\n"
                f"`{prefix}bypassrole grant <@role> <@member>` - Safely grant a bypass role to a member\n"
                f"`{prefix}bypassrole actions` - View all available action types"
            ),
            inline=False
        )
        embed.set_footer(text="Only Server Owner & Extra Owners can configure bypass roles")
        await ctx.send(embed=embed)

    @bypassrole.command(name="actions")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def show_actions(self, ctx):
        """List all valid action types for bypass roles"""
        lines = [f"• `{k}` - {v}" for k, v in ACTIONS_MAP.items()]
        embed = discord.Embed(
            title="📋 Available Action Types",
            description="\n".join(lines),
            color=0x000000
        )
        await ctx.send(embed=embed)

    @bypassrole.command(name="create_all", aliases=["setup", "autocreate"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.guild_only()
    async def create_all_bypass_roles(self, ctx):
        """Automatically creates separate bypass roles for each action in the server!"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can run this command!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("<:icon_cross:1372375094336425986> I don't have `Manage Roles` permission to create roles!")

        msg = await ctx.send("<a:loading:1372989569653538866> Creating separate bypass roles for all actions...")

        created = []
        async with aiosqlite.connect('db/anti.db') as db:
            for action_key, action_name in ACTIONS_MAP.items():
                role_name = f"Bypass - {action_name}"
                try:
                    role = await ctx.guild.create_role(
                        name=role_name,
                        reason=f"Antinuke Separate Bypass Role created by {ctx.author}"
                    )
                    if action_key == 'all':
                        await db.execute("INSERT OR IGNORE INTO bypass_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
                    else:
                        await db.execute("INSERT OR IGNORE INTO action_bypass_roles (guild_id, action_type, role_id) VALUES (?, ?, ?)", (ctx.guild.id, action_key, role.id))
                    created.append(f"• **{action_name}**: {role.mention}")
                except Exception as e:
                    created.append(f"• **{action_name}**: Failed ({e})")
            await db.commit()

        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Separate Bypass Roles Created Successfully!",
            description="\n".join(created),
            color=0x00FF00
        )
        embed.set_footer(text=f"Total: {len(created)} bypass roles registered")
        await msg.edit(content=None, embed=embed)

    @bypassrole.command(name="set")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def set_action_bypass_role(self, ctx, action: str, role: discord.Role):
        """Set a role to bypass a specific action (e.g., !bypassrole set ban @Role)"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can set bypass roles!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        action = action.lower()
        if action not in ACTIONS_MAP:
            return await ctx.send(f"Invalid action! Use `{ctx.prefix}bypassrole actions` to see available actions.")

        if role == ctx.guild.default_role:
            return await ctx.send("Cannot set @everyone as a bypass role!")

        async with aiosqlite.connect('db/anti.db') as db:
            if action == 'all':
                await db.execute("INSERT OR IGNORE INTO bypass_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
            else:
                await db.execute("INSERT OR IGNORE INTO action_bypass_roles (guild_id, action_type, role_id) VALUES (?, ?, ?)", (ctx.guild.id, action, role.id))
            await db.commit()

        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Action Bypass Role Configured",
            description=f"Successfully set {role.mention} as the bypass role for **{ACTIONS_MAP[action]}**.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @bypassrole.command(name="unset")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def unset_action_bypass_role(self, ctx, action: str, role: discord.Role):
        """Remove a role from a specific action bypass"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can remove bypass roles!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        action = action.lower()
        async with aiosqlite.connect('db/anti.db') as db:
            if action == 'all':
                cursor = await db.execute("DELETE FROM bypass_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id))
            else:
                cursor = await db.execute("DELETE FROM action_bypass_roles WHERE guild_id = ? AND action_type = ? AND role_id = ?", (ctx.guild.id, action, role.id))
            await db.commit()

            if cursor.rowcount == 0:
                return await ctx.send(f"{role.mention} was not set for action `{action}`!")

        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Action Bypass Role Removed",
            description=f"Successfully removed {role.mention} from bypass for **{ACTIONS_MAP.get(action, action)}**.",
            color=0x000000
        )
        await ctx.send(embed=embed)

    @bypassrole.command(name="add")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def add_bypass_role(self, ctx, role: discord.Role):
        """Add a full bypass role (all actions)"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can add bypass roles!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        if role == ctx.guild.default_role:
            return await ctx.send("Cannot set @everyone as a bypass role!")

        async with aiosqlite.connect('db/anti.db') as db:
            await db.execute("INSERT OR IGNORE INTO bypass_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
            await db.commit()

        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Full Bypass Role Added",
            description=f"Successfully added {role.mention} (`{role.id}`) to Full Antinuke Bypass.\nMembers with this role will bypass all antinuke restrictions.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @bypassrole.command(name="remove")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def remove_bypass_role(self, ctx, role: discord.Role):
        """Remove a full bypass role"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can remove bypass roles!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        async with aiosqlite.connect('db/anti.db') as db:
            cursor = await db.execute("DELETE FROM bypass_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id))
            await db.execute("DELETE FROM action_bypass_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id))
            await db.commit()
            if cursor.rowcount == 0:
                return await ctx.send(f"{role.mention} is not in the bypass list!")

        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Bypass Role Removed",
            description=f"Successfully removed {role.mention} from Antinuke Bypass.",
            color=0x000000
        )
        await ctx.send(embed=embed)

    @bypassrole.command(name="list", aliases=["show", "config"])
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def list_bypass_roles(self, ctx):
        """Show all general and action-specific bypass roles"""
        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT role_id FROM bypass_roles WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                full_rows = await cursor.fetchall()

            async with db.execute("SELECT action_type, role_id FROM action_bypass_roles WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                action_rows = await cursor.fetchall()

        if not full_rows and not action_rows:
            embed = discord.Embed(
                title="🛡️ Antinuke Bypass Roles",
                description="No bypass roles configured in this server yet.\nUse `bypassrole create_all` or `bypassrole add <@role>`.",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f"🛡️ Antinuke Bypass Roles for {ctx.guild.name}",
            color=0x000000
        )

        if full_rows:
            full_list = []
            for (r_id,) in full_rows:
                r = ctx.guild.get_role(r_id)
                full_list.append(f"• {r.mention if r else f'`{r_id}`'}")
            embed.add_field(name="👑 **Full Bypass Roles (All Actions)**", value="\n".join(full_list), inline=False)

        if action_rows:
            action_list = []
            for act, r_id in action_rows:
                r = ctx.guild.get_role(r_id)
                action_name = ACTIONS_MAP.get(act, act)
                action_list.append(f"• **{action_name}**: {r.mention if r else f'`{r_id}`'}")
            embed.add_field(name="⚡ **Action-Specific Bypass Roles**", value="\n".join(action_list), inline=False)

        await ctx.send(embed=embed)

    @bypassrole.command(name="grant")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    async def grant_bypass_role(self, ctx, role: discord.Role, member: discord.Member):
        """Safely grant any registered bypass role to a member"""
        if not await self.is_owner_or_extraowner(ctx):
            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Only the Server Owner or Extra Owners can grant bypass roles!",
                color=0x000000
            )
            return await ctx.send(embed=embed)

        async with aiosqlite.connect('db/anti.db') as db:
            async with db.execute("SELECT 1 FROM bypass_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
                is_full = await cursor.fetchone() is not None
            async with db.execute("SELECT 1 FROM action_bypass_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
                is_action = await cursor.fetchone() is not None

        if not is_full and not is_action:
            return await ctx.send(f"{role.mention} is not registered as a bypass role!")

        if role >= ctx.guild.me.top_role:
            return await ctx.send(f"I cannot assign {role.mention} because it is higher than or equal to my highest role!")

        await member.add_roles(role, reason=f"Bypass role granted by authorized owner {ctx.author}")
        embed = discord.Embed(
            title="<:icon_tick:1372375089668161597> Bypass Role Granted",
            description=f"Successfully granted {role.mention} to {member.mention}.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BypassRoles(bot))
