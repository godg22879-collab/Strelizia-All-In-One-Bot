import discord 
from discord.ext import commands 


class _bypass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 

    """Bypass Commands"""

    def help_custom(self):
        emoji = '<:icon_autorole:1372532056344625213>'
        label = "Bypass Commands"
        description = "Antinuke Bypass & Action Roles"
        return emoji, label, description 

    @commands.group()
    async def __Bypass__(self, ctx: commands.Context):
        """`bypassrole` , `bypassrole create_all` , `bypassrole setup` , `bypassrole set <action> <@role>` , `bypassrole unset <action> <@role>` , `bypassrole add <@role>` , `bypassrole remove <@role>` , `bypassrole list` , `bypassrole grant <@role> <@member>` , `bypassrole actions`\n\n__**Supported Actions**__\n`ban` , `kick` , `memup` , `voicemod` , `chcr` , `chdl` , `chup` , `rlcr` , `rldl` , `rlup` , `meneve` , `mngweb` , `mngstemo` , `serverup` , `all`"""
