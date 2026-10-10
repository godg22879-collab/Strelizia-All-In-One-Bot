from __future__ import annotations 
from discord .ext import commands 
import os 
import discord 
import aiohttp 
import json 
import jishaku 
import asyncio 
import typing 
from typing import List 
import aiosqlite 
from utils.config import OWNER_IDS 
from utils.Tools import getConfig ,updateConfig 
from .Context import Context 
from discord .ext import commands ,tasks 
from colorama import Fore ,Style ,init 
import importlib 
import inspect 
from utils .Tools import get_ignore_data 
import random 


init (autoreset =True )

extensions :List [str ]=[
"cogs"
]

class Strelizia (commands .AutoShardedBot ):

    def __init__ (self ,*arg ,**kwargs ):
        intents =discord .Intents .all ()
        intents .presences =True 
        intents .members =True 
        super ().__init__ (command_prefix =self .get_prefix ,
        case_insensitive =True ,
        intents =intents ,
        status =discord .Status .online ,
        strip_after_prefix =True ,
        owner_ids =OWNER_IDS ,
        allowed_mentions =discord .AllowedMentions (
        everyone =False ,replied_user =False ,roles =False ),
        sync_commands_debug =True ,
        sync_commands =True )


        self .status_messages =[
        {"type":discord .ActivityType .watching ,"name":"over D4Hz HQ"},
        {"type":discord .ActivityType .listening ,"name":"to your commands"},
        {"type":discord .ActivityType .playing ,"name":"with Discord API"},
        {"type":discord .ActivityType .streaming ,"name":"&help | D4Hz Defense","url":"https://twitch.tv/d4hz"},
        {"type":discord .ActivityType .watching ,"name":"the D4Hz community"},
        {"type":discord .ActivityType .playing ,"name":"in D4Hz's digital space"},
        {"type":discord .ActivityType .listening ,"name":"to D4Hz's security feed"},
        {"type":discord .ActivityType .watching ,"name":"for new members"},
        {"type":discord .ActivityType .playing ,"name":"the role of your assistant"},
        {"type":discord .ActivityType .listening ,"name":"to feedback from D4Hz HQ"},
        {"type":discord .ActivityType .watching ,"name":"D4Hz protect servers"},
        {"type":discord .ActivityType .playing ,"name":"guardian of D4Hz servers"}
        ]
        self .current_status_index =0 

    async def setup_hook (self ):
        await self .load_extensions ()
        self .status_rotation .start ()

        

    async def load_extensions (self ):
        for extension in extensions :
            try :
                await self .load_extension (extension )
            except Exception as e :
                print (
                f"{Fore.RED}{Style.BRIGHT}Failed to load extension {extension}. {e}"
                )


    async def on_connect (self ):
        await self .set_random_status ()

    @tasks .loop (seconds =10 )
    async def status_rotation (self ):
        await self .set_random_status ()

    async def set_random_status (self ):
        status_config =random .choice (self .status_messages )

        if status_config ["type"]==discord .ActivityType .streaming :
            activity =discord .Streaming (
            name =status_config ["name"],
            url =status_config .get ("url","https://twitch.tv/d4hz")
            )
        else :
            activity =discord .Activity (
            type =status_config ["type"],
            name =status_config ["name"]
            )

        await self .change_presence (status =discord .Status .online ,activity =activity )

    @status_rotation .before_loop 
    async def before_status_rotation (self ):
        await self .wait_until_ready ()

    async def send_raw (self ,channel_id :int ,content :str ,
    **kwargs )->typing .Optional [discord .Message ]:
        await self .http .send_message (channel_id ,content ,**kwargs )

    async def invoke_help_command (self ,ctx :Context )->None :
        """Invoke the help command or default help command if help extensions is not loaded."""
        return await ctx .send_help (ctx .command )

    async def fetch_message_by_channel (
    self ,channel :discord .TextChannel ,
    messageID :int )->typing .Optional [discord .Message ]:
        async for msg in channel .history (
        limit =1 ,
        before =discord .Object (messageID +1 ),
        after =discord .Object (messageID -1 ),
        ):
            return msg 

    async def get_prefix (self ,message :discord .Message ):
        env_prefix = os.getenv('PREFIX') or os.getenv('BOT_PREFIX') or '&'
        prefixes = [env_prefix]
        for p in ['!', '&']:
            if p not in prefixes:
                prefixes.append(p)

        if message .guild :
            guild_id =message .guild .id 
            try :
                data =await getConfig (guild_id )
                g_prefix =data .get ("prefix")
                if g_prefix and g_prefix not in prefixes :
                    prefixes .append (g_prefix )
            except Exception :
                pass 

            owner_env = os.getenv("OWNER_IDS", "")
            env_owner_ids = [int(i.strip()) for i in owner_env.split(",") if i.strip().isdigit()]
            all_owners = set(OWNER_IDS + env_owner_ids)

            global_np = os.getenv("NO_PREFIX", "").lower() in ["true", "1", "yes", "all", "on"]
            is_np = global_np
            if not is_np:
                if message.author.id in all_owners or str(message.author.id) in [x.strip() for x in owner_env.split(",")]:
                    is_np = True
                else:
                    try:
                        async with aiosqlite.connect('db/np.db') as db:
                            # Check user no prefix
                            async with db.execute("SELECT id FROM np WHERE id = ?", (message.author.id,)) as cursor:
                                if await cursor.fetchone():
                                    is_np = True
                            # Check server-wide no prefix
                            if not is_np and message.guild:
                                async with db.execute("SELECT guild_id FROM server_np WHERE guild_id = ?", (message.guild.id,)) as c2:
                                    if await c2.fetchone():
                                        is_np = True
                    except Exception:
                        pass

            if is_np:
                if '' not in prefixes:
                    prefixes.append('')
            return commands.when_mentioned_or(*prefixes)(self, message)
        else:
            if '' not in prefixes:
                prefixes.append('')
            return commands.when_mentioned_or(*prefixes)(self, message)


    async def on_message_edit (self ,before ,after ):
        ctx :Context =await self .get_context (after ,cls =Context )
        if before .content !=after .content :
            if after .guild is None or after .author .bot :
                return 
            if ctx .command is None :
                return 
            if type (ctx .channel )=="public_thread":
                return 
            await self .invoke (ctx )
        else :
            return 




def setup_bot ():
    intents =discord .Intents .all ()
    bot =Strelizia (intents =intents )
    return bot 

D4Hz = Strelizia 

"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""
