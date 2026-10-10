import discord
from discord.ext import commands
import asyncio
import datetime

class AntiNukeCoordinator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_recoveries = set()
        self.recent_violations = {}

    def is_recovery_in_progress(self, guild_id):
        return guild_id in self.active_recoveries

    def record_violation(self, guild_id, threshold=2, window_seconds=6):
        """Record an attack violation; returns True if panic threshold breached"""
        now = datetime.datetime.now()
        violations = self.recent_violations.setdefault(guild_id, [])
        violations.append(now)
        # Keep only within time window
        violations = [t for t in violations if (now - t).total_seconds() <= window_seconds]
        self.recent_violations[guild_id] = violations
        return len(violations) >= threshold

    async def initiate_emergency_protocol(self, guild):
        """Emergency lockdown: strips dangerous permissions from all roles below bot and locks server"""
        if guild.id in self.active_recoveries:
            return
        self.active_recoveries.add(guild.id)
        try:
            bot_top_role = guild.me.top_role

            safe_permissions = discord.Permissions(
                administrator=False,
                manage_channels=False,
                manage_roles=False,
                manage_guild=False,
                ban_members=False,
                kick_members=False,
                manage_webhooks=False,
                mention_everyone=False
            )

            # 1. Strip dangerous permissions from all roles below bot
            for role in guild.roles:
                if role < bot_top_role and not role.is_default() and not role.managed:
                    if any([
                        role.permissions.administrator,
                        role.permissions.manage_roles,
                        role.permissions.manage_channels,
                        role.permissions.ban_members,
                        role.permissions.kick_members,
                        role.permissions.manage_guild,
                        role.permissions.manage_webhooks
                    ]):
                        try:
                            # Keep non-dangerous perms, strip dangerous
                            new_perms = role.permissions
                            new_perms.update(
                                administrator=False,
                                manage_channels=False,
                                manage_roles=False,
                                manage_guild=False,
                                ban_members=False,
                                kick_members=False,
                                manage_webhooks=False
                            )
                            await role.edit(permissions=new_perms, reason="EMERGENCY LOCKDOWN: Rapid Nuke Detected")
                            await asyncio.sleep(0.3)
                        except Exception:
                            continue

            # 2. Lockdown default role (@everyone) send messages temporarily
            try:
                default_role = guild.default_role
                if default_role.permissions.send_messages:
                    new_default_perms = default_role.permissions
                    new_default_perms.update(send_messages=False, send_messages_in_threads=False)
                    await default_role.edit(permissions=new_default_perms, reason="EMERGENCY LOCKDOWN: Anti-Raid Freeze")
            except Exception:
                pass

            # 3. Notify Guild Owner
            try:
                if guild.owner:
                    embed = discord.Embed(
                        title="🚨 EMERGENCY LOCKDOWN TRIGGERED",
                        description=f"Rapid nuke or malicious activity was detected in **{guild.name}**!\n"
                                    f"The bot has automatically stripped dangerous permissions from mod/admin roles "
                                    f"and frozen the server to protect your community.",
                        color=0xFF0000
                    )
                    embed.set_footer(text="D4Hz Anti-Nuke Emergency Defense")
                    await guild.owner.send(embed=embed)
            except Exception:
                pass

        finally:
            await asyncio.sleep(10)
            self.active_recoveries.discard(guild.id)

async def setup(bot):
    await bot.add_cog(AntiNukeCoordinator(bot))
