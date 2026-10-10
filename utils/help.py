import discord 
import functools 
import re
from utils .Tools import *

def safe_select_emoji(bot, emoji_val):
    if not emoji_val:
        return None
    match = re.search(r':(\d+)>', str(emoji_val))
    if match:
        eid = int(match.group(1))
        if bot and hasattr(bot, 'emojis'):
            if any(e.id == eid for e in bot.emojis):
                return emoji_val
        if bot and hasattr(bot, 'get_emoji') and bot.get_emoji(eid):
            return emoji_val
        return None
    return emoji_val

def to_serif_bold(text: str) -> str:
    if not text:
        return text
    res = []
    for char in text:
        code = ord(char)
        if 65 <= code <= 90:
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:
            res.append(chr(0x1D7CE + (code - 48)))
        else:
            res.append(char)
    return "".join(res)



class Dropdown (discord .ui .Select ):

    def __init__ (self ,ctx ,options ,placeholder ="Choose a Category for Help",row =None ):
        super ().__init__ (placeholder =placeholder ,
        min_values =1 ,
        max_values =1 ,
        options =options ,
        row =row )
        self .invoker =ctx .author 

    async def callback (self ,interaction :discord .Interaction ):
        if self .invoker ==interaction .user :
            index =self .view .find_index_from_select (self .values [0 ])
            if not index :
                index =0 
            await self .view .set_page (index ,interaction )
        else :
            await interaction .response .send_message (
            "You must run this command to interact with it.",ephemeral =True )


class Button (discord .ui .Button ):

    def __init__ (self ,command ,ctx ,label ,style :discord .ButtonStyle ,emoji =None ,args =None ):
        disable =False 
        if args ==-1 or args ==0 :
            disable =True 
        super ().__init__ (label =label ,style =style ,emoji =emoji ,disabled =disable )
        self .command =command 
        self .invoker =ctx .author 
        self .args =args 

    async def callback (self ,interaction :discord .Interaction ):
        if self .invoker ==interaction .user :
            if self .args or self .args ==0 :
                func =functools .partial (self .command ,self .args ,interaction )
                await func ()
            else :
                await self .command (interaction )
        else :
            await interaction .response .send_message (
            "You must run this command to interact with it.",ephemeral =True )


class View (discord .ui .View ):

    def __init__ (self ,mapping :dict ,ctx :discord .ext .commands .context .Context ,homeembed :discord .embeds .Embed ,ui :int ):
        super ().__init__ (timeout =None )
        self .mapping ,self .ctx ,self .home =mapping ,ctx ,homeembed 
        self .index ,self .buttons =0 ,None 
        self .current_page =0 

        self .options ,self .embeds ,self .total_pages =self .gen_embeds ()

        if ui ==0 :

            self .add_item (Dropdown (ctx =self .ctx ,options =self .options ))
        elif ui ==1 :

            self .buttons =self .add_buttons ()
        elif ui ==2 :

            self .buttons =self .add_buttons ()

            mid_point =len (self .options )//2 
            options_1 =self .options [:mid_point ]
            options_2 =self .options [mid_point :]


            if options_1 :
                self .add_item (Dropdown (ctx =self .ctx ,options =options_1 ,placeholder ="Core Commands",row =1 ))

            if options_2 :
                self .add_item (Dropdown (ctx =self .ctx ,options =options_2 ,placeholder ="Extra Commands",row =2 ))
        else :

            self .buttons =self .add_buttons ()
            self .add_item (Dropdown (ctx =self .ctx ,options =self .options ))

    def add_buttons (self ):

        self.homeB = discord.ui.Button(
            label="",
            emoji=safe_select_emoji(self.ctx.bot, "<:SageDoubleArrowLeft:1385846432535412758>") or "⏪",
            style=discord.ButtonStyle.secondary
        )
        self.homeB.callback = self.home_callback

        self.backB = discord.ui.Button(
            label="",
            emoji=safe_select_emoji(self.ctx.bot, "<:arrow_left:1385846548625363117>") or "◀",
            style=discord.ButtonStyle.secondary
        )
        self.backB.callback = self.back_callback

        self.nextB = discord.ui.Button(
            label="",
            emoji=safe_select_emoji(self.ctx.bot, "<:arrow_right:1385846525204103252>") or "▶",
            style=discord.ButtonStyle.secondary
        )
        self.nextB.callback = self.next_callback

        self.lastB = discord.ui.Button(
            label="",
            emoji=safe_select_emoji(self.ctx.bot, "<:SageDoubleArrowRight:1385846409902948362>") or "⏩",
            style=discord.ButtonStyle.secondary
        )
        self.lastB.callback = self.last_callback 

        buttons =[self .homeB ,self .backB ,self .nextB ,self .lastB ]
        for button in buttons :
            self .add_item (button )
        return buttons 

    async def home_callback (self ,interaction :discord .Interaction ):
        if interaction .user !=self .ctx .author :
            await interaction .response .send_message ("You must run this command to interact with it.",ephemeral =True )
            return 
        await self .set_page (0 ,interaction )

    async def back_callback (self ,interaction :discord .Interaction ):
        if interaction .user !=self .ctx .author :
            await interaction .response .send_message ("You must run this command to interact with it.",ephemeral =True )
            return 
        current_page =self .index -1 if self .index >0 else len (self .embeds )-1 
        await self .set_page (current_page ,interaction )

    async def quit_callback (self ,interaction :discord .Interaction ):
        if interaction .user !=self .ctx .author :
            await interaction .response .send_message ("You must run this command to interact with it.",ephemeral =True )
            return 
        await self .quit (interaction )

    async def next_callback (self ,interaction :discord .Interaction ):
        if interaction .user !=self .ctx .author :
            await interaction .response .send_message ("You must run this command to interact with it.",ephemeral =True )
            return 
        current_page =self .index +1 if self .index <len (self .embeds )-1 else 0 
        await self .set_page (current_page ,interaction )

    async def last_callback (self ,interaction :discord .Interaction ):
        if interaction .user !=self .ctx .author :
            await interaction .response .send_message ("You must run this command to interact with it.",ephemeral =True )
            return 
        await self .set_page (len (self .embeds )-1 ,interaction )

    def find_index_from_select (self ,value ):
        i =0 
        used_labels =set ()

        for cog in self .get_cogs ():

            if cog .__class__ .__name__ =="Roleplay":
                continue 

            if "help_custom"in dir (cog ):
                _ ,label ,_ =cog .help_custom ()


                original_label =label 
                counter =1 
                while label in used_labels :
                    label =f"{original_label} {counter}"
                    counter +=1 

                used_labels .add (label )


                if label ==value or value .startswith (original_label +" "):
                    return i +1 
                i +=1 

        return 0 

    def get_cogs (self ):
        return list (self .mapping .keys ())

    def gen_embeds (self ):
        options ,embeds =[],[]
        total_pages =0 
        used_labels =set ()

        home_emoji = safe_select_emoji(self.ctx.bot, '<:help:1388729258263969903>')
        options.append(
            discord.SelectOption(
                label=to_serif_bold("Home"),
                value="Home",
                emoji=home_emoji,
                description=""
            )
        )
        embeds.append(self.home)
        total_pages += 1
        used_labels.add("Home")

        for cog in self.get_cogs():

            if cog.__class__.__name__ == "Roleplay":
                continue 

            if "help_custom" in dir(cog):
                emoji, label, description = cog.help_custom()

                original_label = label 
                counter = 1 
                while label in used_labels:
                    label = f"{original_label} {counter}"
                    counter += 1 

                used_labels.add(label)
                sel_emoji = safe_select_emoji(self.ctx.bot, emoji)
                options.append(
                    discord.SelectOption(
                        label=to_serif_bold(label),
                        value=label,
                        emoji=sel_emoji,
                        description=description
                    )
                )

                embed = discord.Embed(
                    title=f"{emoji} {to_serif_bold(original_label)}",
                    color=0x000000
                )

                for command in cog .get_commands ():
                    params =""
                    for param in command .clean_params :
                        if param not in ["self","ctx"]:
                            params +=f" <{param}>"


                    help_text =command .help or "No description available"
                    if len (help_text )>1020 :
                        help_text =help_text [:1017 ]+"..."

                    embed .add_field (name =f"{to_serif_bold(command.name)}{params}",
                    value =f"{help_text}\n\u200b",
                    inline =False )

                embeds .append (embed )
                total_pages +=1 

        self .home .set_footer (text =f"• 𝐇𝐞𝐥𝐩 𝐩𝐚𝐠𝐞 1/{total_pages} | 𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐛𝐲: {self.ctx.author.display_name}",
        icon_url =f"{self.ctx.bot.user.avatar.url}")

        return options ,embeds ,total_pages 

    async def quit (self ,interaction :discord .Interaction ):
        await interaction .response .defer ()
        await interaction .delete_original_response ()

    async def to_page (self ,page :int ,interaction :discord .Interaction ):
        if not self .index +page <0 or not self .index +page >len (self .options ):
            await self .set_index (page )
            embed =self .embeds [self .index ]
            embed .set_footer (text =f"• 𝐇𝐞𝐥𝐩 𝐩𝐚𝐠𝐞 {self.index + 1}/{self.total_pages} | 𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐛𝐲: {self.ctx.author.display_name}",
            icon_url =f"{self.ctx.bot.user.avatar.url}")
            await interaction .response .edit_message (embed =embed ,view =self )

    async def set_page (self ,page :int ,interaction :discord .Interaction ):
        self .index =page 
        self .current_page =page 
        await self .to_page (0 ,interaction )

    async def set_index (self ,page ):
        self .index +=page 
        if self .buttons :
            for button in self .buttons [0 :-1 ]:
                button .disabled =False 
            if self .index ==0 :
                self .backB .disabled =True 
            elif self .index ==len (self .options )-1 :
                self .nextB .disabled =True 

    async def set_last_page (self ,interaction :discord .Interaction ):
        await self .set_page (len (self .options )-1 ,interaction )
"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""
