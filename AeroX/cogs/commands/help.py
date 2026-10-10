import discord 
from discord .ext import commands 
from discord import app_commands ,Interaction 
from difflib import get_close_matches 
from contextlib import suppress 
from core import Context 
from core .Strelizia import Strelizia 
from core .Cog import Cog 
from utils .Tools import getConfig 
from itertools import chain 
import json 
from utils import help as vhelp 
from utils import Paginator ,DescriptionEmbedPaginator ,FieldPagePaginator ,TextPaginator 
import asyncio 
from utils .config import serverLink 
from utils .Tools import *

color =0x000000 
client =Strelizia ()

class HelpCommand (commands .HelpCommand ):

  async def send_ignore_message (self ,ctx ,ignore_type :str ):

    if ignore_type =="channel":
      await ctx .reply (f"This channel is ignored.",mention_author =False )
    elif ignore_type =="command":
      await ctx .reply (f"{ctx.author.mention} This Command, Channel, or You have been ignored here.",delete_after =6 )
    elif ignore_type =="user":
      await ctx .reply (f"You are ignored.",mention_author =False )

  async def on_help_command_error (self ,ctx ,error ):
    if isinstance (error ,commands .CommandNotFound ):
      embed =discord .Embed (
      color =0x000000 ,
      description =f"No command or category named `{ctx.invoked_with}` found."
      )
      embed .set_author (name ="Command Not Found",icon_url =ctx .bot .user .avatar .url )
      embed .set_footer (text =f"Use {ctx.prefix}help to see all commands")
      await ctx .reply (embed =embed ,delete_after =10 )
    else :

      await ctx .reply ("An error occurred while processing the help command.",delete_after =10 )

  async def command_not_found (self ,string :str )->str :
    return f"No command called `{string}` found."

  def create_strelizia_mapping (self ,mapping ):
    """Create a filtered mapping that only includes cogs from cogs/strelizia directories"""
    strelizia_mapping ={}


    allowed_cog_classes ={

    '_general','_voice','_games','_welcome','ticket','__sticky','__boost',
    '_automod','_antinuke','_music','_extra','_fun','_moderation','_giveaway',

    '_leveling','_ai','_server','RoleplayHelp','VerificationHelp','YTVerifyHelp',
    '_tracking','_logging','_counting','_Backup','_crew','_ignore','_bypass'
    }

    for cog ,commands in mapping .items ():
      if cog and hasattr (cog ,'__class__'):
        cog_class_name =cog .__class__ .__name__ 

        if cog_class_name in allowed_cog_classes and hasattr (cog ,'help_custom'):
          strelizia_mapping [cog ]=commands 

    return strelizia_mapping 

  async def send_bot_help (self ,mapping ):
    ctx =self .context 
    check_ignore =await ignore_check ().predicate (ctx )
    check_blacklist =await blacklist_check ().predicate (ctx )

    if not check_blacklist :
      return 

    if not check_ignore :
      await self .send_ignore_message (ctx ,"command")
      return 


    filtered_mapping =self .create_strelizia_mapping (mapping )

    embed =discord .Embed (description ="<a:Strelizia_loading:1373173756113195081> **Loading Help menu...**",color =color )
    ok =await self .context .reply (embed =embed )
    data =await getConfig (self .context .guild .id )
    prefix =data ["prefix"]
    filtered =await self .filter_commands (self .context .bot .walk_commands (),
    sort =True )
    slash =len ([
    cmd for cmd in self .context .bot .tree .get_commands ()
    if isinstance (cmd ,app_commands .Command )
    ])
    embed =discord .Embed (
    title ="𝐇𝐞𝐥𝐩 𝐌𝐞𝐧𝐮",
    color =0x000000 
    )
    d4hz_path = os.path.abspath("D4Hz.gif") if os.path.exists("D4Hz.gif") else (os.path.abspath("../D4Hz.gif") if os.path.exists("../D4Hz.gif") else None)
    d4hz_file = discord.File(d4hz_path, filename="D4Hz.gif") if d4hz_path else None
    if d4hz_file:
        embed.set_image(url="attachment://D4Hz.gif")
    else:
        embed.set_image(url="https://cdn.discordapp.com/banners/1372468860435042344/2200c89d12a45d8cf648694ad30535f8.png?size=512")

    embed .add_field (
    name ="<:help:1388729258263969903> __**𝐆𝐞𝐧𝐞𝐫𝐚𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**__",
    value =">>> \n <a:vcwaiting:1523295680875987045> 𝐕𝐨𝐢𝐜𝐞\n"
    " <:heads:1385235448003039273> 𝐆𝐚𝐦𝐞𝐬\n"
    " <:join_icon:1374287302934790235> 𝐖𝐞𝐥𝐜𝐨𝐦𝐞𝐫\n"
    " <a:thread1:1523295595689934888> 𝐓𝐢𝐜𝐤𝐞𝐭𝐢𝐧𝐠\n"
    " <:icon_edit:1372531753343778908> 𝐀𝐮𝐭𝐨 𝐒𝐞𝐭𝐮𝐩\n"
    " <:icon_autorole:1372532056344625213> 𝐀𝐮𝐭𝐨𝐫𝐨𝐥𝐞\n"
    " <:fun:1373621697776975962> 𝐅𝐮𝐧\n"
    " <:icon_ignore:1373173575078379590> 𝐈𝐠𝐧𝐨𝐫𝐞 𝐂𝐡𝐚𝐧𝐧𝐞𝐥𝐬\n"
    " <:logging_icons:1377373741268471900> 𝐋𝐨𝐠𝐠𝐢𝐧𝐠\n"
    " <:plus_icons:1377949309751791717> 𝐂𝐨𝐮𝐧𝐭𝐢𝐧𝐠\n"
    " <:leveling_icons:1378293065273442395> 𝐋𝐞𝐯𝐞𝐥𝐢𝐧𝐠\n"
    " <:tracking_icons:1378293093219962921> 𝐓𝐫𝐚𝐜𝐤𝐢𝐧𝐠\n"
    )

    embed .add_field (
    name ="<:strelizia_owner:1374273169086484480> __**𝐁𝐨𝐭 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**__",
    value =">>> \n <:admin:1373949463814738002> 𝐒𝐞𝐜𝐮𝐫𝐢𝐭𝐲\n"
    " <:Automod:1374274713865687120> 𝐀𝐮𝐭𝐨𝐦𝐨𝐝\n"
    " <:icons_channel:1381865641463517325> 𝐔𝐭𝐢𝐥𝐢𝐭𝐲\n"
    " <:music:1373174130907807814> 𝐌𝐮𝐬𝐢𝐜\n"
    " <a:ban:1376600344502468618> 𝐌𝐨𝐝𝐞𝐫𝐚𝐭𝐢𝐨𝐧\n"
    " <:icon_categories:1373173618858659901> 𝐆𝐞𝐧𝐞𝐫𝐚𝐥\n"
    " <:Giveaway:1373566437104554047> 𝐆𝐢𝐯𝐞𝐚𝐰𝐚𝐲\n"
    " <:Ai:1375898214087135263> 𝐀𝐫𝐭𝐢𝐟𝐢𝐜𝐢𝐚𝐥 𝐈𝐧𝐭𝐞𝐥𝐥𝐢𝐠𝐞𝐧𝐜𝐞\n"
    " <:backup_icons:1376857941986250844> 𝐁𝐚𝐜𝐤𝐮𝐩\n"
    " <:icons_tv:1381541359055540255> 𝐑𝐨𝐥𝐞play\n"
    " <:staff_icons:1381539824711766046> 𝐒𝐭𝐚𝐟𝐟 𝐀𝐩𝐩𝐥𝐢𝐜𝐚𝐭𝐢𝐨𝐧\n"
    " <:icon_autorole:1372532056344625213> 𝐁𝐲𝐩𝐚𝐬𝐬 𝐑𝐨𝐥𝐞𝐬\n"
    )

    embed .set_footer (
    text =f"𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐁𝐲 {self.context.author}",
    )

    embed .set_thumbnail (url =self .context .author .avatar .url )
    view =vhelp .View (mapping =filtered_mapping ,
    ctx =self .context ,
    homeembed =embed ,
    ui =2 )
    await asyncio .sleep (0.1 )
    if d4hz_file :
        await ok .edit (embed =embed ,view =view ,attachments =[d4hz_file ])
    else :
        await ok .edit (embed =embed ,view =view )

  async def send_command_help (self ,command ):
    ctx =self .context 
    check_ignore =await ignore_check ().predicate (ctx )
    check_blacklist =await blacklist_check ().predicate (ctx )

    if not check_blacklist :
      return 

    if not check_ignore :
      self .send_ignore_message (ctx ,"command")
      return 

    description =command .description or command .help or 'No Help Provided...'
    embed =discord .Embed (
    description =
    f"""```xml
<[] = optional | ‹› = required
Don't type these while using Commands>```\n>>> {description}""",
    color =0xffffff )
    alias =' | '.join (command .aliases )if command .aliases else "No Aliases"
    embed .add_field (name ="**Aliases**",value =alias ,inline =False )
    embed .add_field (name ="**Usage**",value =f"`{self.context.prefix}{command.signature}`\n")
    embed .set_author (name =f"{command.qualified_name.title()} Command",
    icon_url =self .context .bot .user .display_avatar .url )
    await self .context .reply (embed =embed ,mention_author =False )

  def get_command_signature (self ,command :commands .Command )->str :
    parent =command .full_parent_name 
    if len (command .aliases )>0 :
      aliases =' | '.join (command .aliases )
      fmt =f'[{command.name} | {aliases}]'
      if parent :
        fmt =f'{parent}'
      alias =f'[{command.name} | {aliases}]'
    else :
      alias =command .name if not parent else f'{parent} {command.name}'
    return f'{alias} {command.signature}'

  def common_command_formatting (self ,embed_like ,command ):
    embed_like .title =self .get_command_signature (command )
    if command .description :
      embed_like .description =f'{command.description}\n\n{command.help}'
    else :
      embed_like .description =command .help or 'No help found...'

  async def send_group_help (self ,group ):
    ctx =self .context 
    check_ignore =await ignore_check ().predicate (ctx )
    check_blacklist =await blacklist_check ().predicate (ctx )

    if not check_blacklist :
      return 

    if not check_ignore :
      await self .send_ignore_message (ctx ,"command")
      return 

    entries =[
    (
    f"➜ `{self.context.prefix}{cmd.qualified_name}`\n",
    f"{cmd.description or cmd.short_doc or 'No description provided...'}\n\u200b"
    )
    for cmd in group .commands 
    ]

    count =len (group .commands )

    paginator =Paginator (source =FieldPagePaginator (
    entries =entries ,
    title =f"{group.qualified_name.title()} [{count}]",
    description ="< > Duty | [ ] Optional\n",
    color =color ,
    per_page =4 ),
    ctx =self .context )
    await paginator .paginate ()

  async def send_cog_help (self ,cog ):
    ctx =self .context 
    check_ignore =await ignore_check ().predicate (ctx )
    check_blacklist =await blacklist_check ().predicate (ctx )

    if not check_blacklist :
      return 

    if not check_ignore :
      await self .send_ignore_message (ctx ,"command")
      return 

    entries =[(
    f"➜ `{self.context.prefix}{cmd.qualified_name}`",
    f"{cmd.description or cmd.short_doc or 'No description provided...'}\n\u200b"
    )for cmd in cog .get_commands ()]
    paginator =Paginator (source =FieldPagePaginator (
    entries =entries ,
    title =f"{cog.qualified_name.title()} ({len(cog.get_commands())})",
    description ="< > Duty | [ ] Optional\n\n",
    color =color ,
    per_page =4 ),
    ctx =self .context )
    await paginator .paginate ()

class Help (Cog ,name ="help"):

  def __init__ (self ,client :Strelizia ):
    self .bot =client 
    self ._original_help_command =client .help_command 
    attributes ={
    'name':"help",
    'aliases':['h', 'cmds', 'commands', 'halp', 'menu'],
    'cooldown':commands .CooldownMapping .from_cooldown (1 ,5 ,commands .BucketType .user ),
    'help':'Shows help about bot, a command or a category'
    }
    client .help_command =HelpCommand (command_attrs =attributes )
    client .help_command .cog =self 

  async def cog_unload (self ):
    self .help_command =self ._original_help_command 



"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""
"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""