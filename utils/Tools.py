import json ,sys ,os 
import discord 
from discord .ext import commands 
from core import Context 
from utils.config import OWNER_IDS 
import aiosqlite 
import asyncio 

async def setup_db ():
  async with aiosqlite .connect ('db/prefix.db')as db :
    await db .execute ('''
      CREATE TABLE IF NOT EXISTS prefixes (
        guild_id INTEGER PRIMARY KEY,
        prefix TEXT NOT NULL
      )
    ''')
    await db .commit ()


asyncio .run (setup_db ())

async def is_topcheck_enabled (guild_id :int ):
    async with aiosqlite .connect ('db/topcheck.db')as db :
        async with db .execute ("SELECT enabled FROM topcheck WHERE guild_id = ?",(guild_id ,))as cursor :
            row =await cursor .fetchone ()
            return row is not None and row [0 ]==1 



def read_json (file_path ):
    try :
        with open (file_path ,"r")as file :
            return json .load (file )
    except (FileNotFoundError ,json .JSONDecodeError ):
        return {"guilds":{}}

def write_json (file_path ,data ):
    with open (file_path ,"w")as file :
        json .dump (data ,file ,indent =4 ,ensure_ascii =False )

def get_or_create_guild_config (file_path ,guild_id ,default_config ):
    data =read_json (file_path )
    if "guilds"not in data :
        data ["guilds"]={}

    guild_id_str =str (guild_id )
    if guild_id_str not in data ["guilds"]:
        data ["guilds"][guild_id_str ]=default_config 
        write_json (file_path ,data )
    return data ["guilds"][guild_id_str ]

def update_guild_config (file_path ,guild_id ,new_data ):
    data =read_json (file_path )
    if "guilds"not in data :
        data ["guilds"]={}

    data ["guilds"][str (guild_id )]=new_data 
    write_json (file_path ,data )

def getIgnore (guild_id ):
    default_config ={
    "channel":[],
    "role":None ,
    "user":[],
    "bypassrole":None ,
    "bypassuser":[],
    "commands":[]
    }
    return get_or_create_guild_config ("ignore.json",guild_id ,default_config )

def updateignore (guild_id ,data ):
    update_guild_config ("ignore.json",guild_id ,data )





async def getConfig (guildID ):
  async with aiosqlite .connect ('db/prefix.db')as db :
    async with db .execute ("SELECT prefix FROM prefixes WHERE guild_id = ?",(guildID ,))as cursor :
      row =await cursor .fetchone ()
      if row :
        return {"prefix":row [0 ]}
      else :
        # Use BOT_PREFIX from environment variable or default to "&"
        import os
        default_prefix = os.getenv('BOT_PREFIX', '&')
        defaultConfig ={"prefix": default_prefix}
        await updateConfig (guildID ,defaultConfig )
        return defaultConfig 

async def updateConfig (guildID ,data ):
  async with aiosqlite .connect ('db/prefix.db')as db :
    await db .execute (
    "INSERT OR REPLACE INTO prefixes (guild_id, prefix) VALUES (?, ?)",
    (guildID ,data ["prefix"])
    )
    await db .commit ()

async def updateAllGuildsPrefixFromEnv():
  """Update prefix for all guilds to use the current BOT_PREFIX from environment"""
  import os
  new_prefix = os.getenv('BOT_PREFIX', '&')
  
  async with aiosqlite .connect ('db/prefix.db')as db :
    # Update all existing guild prefixes to the new environment prefix
    await db .execute ("UPDATE prefixes SET prefix = ?", (new_prefix,))
    await db .commit ()



def restart_program ():
  python =sys .executable 
  os .execl (python ,python ,*sys .argv )


def blacklist_check ():

  async def predicate (ctx ):
    async with aiosqlite .connect ('db/block.db')as db :
      cursor =await db .execute ("SELECT 1 FROM user_blacklist WHERE user_id = ?",(str (ctx .author .id ),))
      user_blacklisted =await cursor .fetchone ()
      if user_blacklisted :
        return False 

      cursor =await db .execute ("SELECT 1 FROM guild_blacklist WHERE guild_id = ?",(str (ctx .guild .id ),))
      guild_blacklisted =await cursor .fetchone ()
      if guild_blacklisted :
        return False 

    return True 

  return commands .check (predicate )


async def get_ignore_data (guild_id :int )->dict :
    async with aiosqlite .connect ("db/ignore.db")as db :
        data ={
        "channel":set (),
        "user":set (),
        "command":set (),
        "bypassuser":set (),
        }

        async with db .execute ("SELECT channel_id FROM ignored_channels WHERE guild_id = ?",(guild_id ,))as cursor :
            channels =await cursor .fetchall ()
            data ["channel"]={str (channel_id )for (channel_id ,)in channels }

        async with db .execute ("SELECT user_id FROM ignored_users WHERE guild_id = ?",(guild_id ,))as cursor :
            users =await cursor .fetchall ()
            data ["user"]={str (user_id )for (user_id ,)in users }

        async with db .execute ("SELECT command_name FROM ignored_commands WHERE guild_id = ?",(guild_id ,))as cursor :
            commands =await cursor .fetchall ()
            data ["command"]={command_name .strip ().lower ()for (command_name ,)in commands }

        async with db .execute ("SELECT user_id FROM bypassed_users WHERE guild_id = ?",(guild_id ,))as cursor :
            bypass_users =await cursor .fetchall ()
            data ["bypassuser"]={str (user_id )for (user_id ,)in bypass_users }

    return data 

def ignore_check ():
    async def predicate (ctx ):
        data =await get_ignore_data (ctx .guild .id )
        ch =data ["channel"]
        iuser =data ["user"]
        cmd =data ["command"]
        buser =data ["bypassuser"]

        if str (ctx .author .id )in buser :
            return True 
        if str (ctx .channel .id )in ch or str (ctx .author .id )in iuser :
            return False 

        command_name =ctx .command .name .strip ().lower ()
        aliases =[alias .strip ().lower ()for alias in ctx .command .aliases ]
        if command_name in cmd or any (alias in cmd for alias in aliases ):
            return False 

        return True 

    return commands .check (predicate )

def top_check ():
    async def predicate (ctx ):
        try :
            if not ctx .guild :
                return True 

            if getattr (ctx ,"invoked_with",None )in ["help","h"]:
                return True 

            topcheck_enabled =await is_topcheck_enabled (ctx .guild .id )

            if not topcheck_enabled :
                return True 

            if ctx .author !=ctx .guild .owner and ctx .author .top_role .position <=ctx .guild .me .top_role .position :
                embed =discord .Embed (
                title ="<:Denied:1294218790082711553> Access Denied",
                description ="Your top role must be at a **higher** position than my top role.",
                color =0x000000 
                )
                embed .set_footer (
                text =f"“{ctx.command.qualified_name}” command executed by {ctx.author}",
                icon_url =ctx .author .avatar .url if ctx .author .avatar else ctx .author .default_avatar .url 
                )
                await ctx .send (embed =embed )
                return False 

            return True 
        except Exception :

            return True 

    return commands .check (predicate )


_handled_errors =set ()

def is_error_handled (ctx ):
    """Check if error for this command is already being handled"""
    command_key =(ctx .message .id ,ctx .command .name )
    return command_key in _handled_errors 

def mark_error_handled (ctx ):
    """Mark error as handled"""
    command_key =(ctx .message .id ,ctx .command .name )
    _handled_errors .add (command_key )
async def check_action_bypass(guild, executor, action_type=None):
    if executor.id == guild.owner_id:
        return True
    owner_env = os.getenv("OWNER_IDS", "")
    env_owner_ids = [int(i.strip()) for i in owner_env.split(",") if i.strip().isdigit()]
    if executor.id in OWNER_IDS or executor.id in env_owner_ids:
        return True
    if executor.bot:
        return False

    async with aiosqlite.connect('db/anti.db') as db:
        async with db.execute("SELECT 1 FROM extraowners WHERE guild_id = ? AND owner_id = ?", (guild.id, executor.id)) as cursor:
            if await cursor.fetchone():
                return True

        if action_type:
            try:
                async with db.execute(f"SELECT {action_type} FROM whitelisted_users WHERE guild_id = ? AND user_id = ?", (guild.id, executor.id)) as cursor:
                    wl = await cursor.fetchone()
                    if wl and wl[0]:
                        return True
            except Exception:
                pass

        # Resolve member object if executor is a discord.User from audit logs
        member = executor if isinstance(executor, discord.Member) else guild.get_member(executor.id)
        if member is None and not executor.bot:
            try:
                member = await guild.fetch_member(executor.id)
            except Exception:
                member = None

        if member:
            role_ids = [r.id for r in member.roles if not r.is_default()]
            if role_ids:
                placeholders = ",".join("?" for _ in role_ids)
                async with db.execute(f"SELECT 1 FROM bypass_roles WHERE guild_id = ? AND role_id IN ({placeholders})", (guild.id, *role_ids)) as cursor:
                    if await cursor.fetchone():
                        return True

                if action_type:
                    async with db.execute(f"SELECT 1 FROM action_bypass_roles WHERE guild_id = ? AND action_type IN (?, 'all') AND role_id IN ({placeholders})", (guild.id, action_type, *role_ids)) as cursor:
                        if await cursor.fetchone():
                            return True
    return False

async def strip_and_ban_executor(guild, executor, reason):
    """Strips all roles, server mutes/deafens if in voice, and bans the executor."""
    member = guild.get_member(executor.id) if isinstance(executor, (discord.User, discord.Member)) else None
    if member:
        # Strip all roles below bot's top role
        try:
            roles_to_keep = [r for r in member.roles if r >= guild.me.top_role or r.is_default()]
            if len(roles_to_keep) != len(member.roles):
                await member.edit(roles=roles_to_keep, reason=f"Stripping roles: {reason}")
        except Exception:
            pass

        # Server mute and deafen if currently in a voice channel
        if getattr(member, 'voice', None):
            try:
                await member.edit(mute=True, deafen=True, reason=f"Voice lockdown: {reason}")
            except Exception:
                pass

    # Straight ban executor
    retries = 3
    while retries > 0:
        try:
            await guild.ban(executor, reason=reason)
            return
        except discord.Forbidden:
            return
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = e.response.headers.get('Retry-After', 1)
                await asyncio.sleep(float(retry_after))
                retries -= 1
            else:
                return
        except Exception:
            return

def antinuke_mod_check(action_type):
    async def predicate(ctx):
        try:
            if not ctx.guild:
                return True
            if ctx.author.id == ctx.guild.owner_id:
                return True

            async with aiosqlite.connect('db/anti.db') as db:
                async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                    status = await cursor.fetchone()
                if not status or not status[0]:
                    return True

            if await check_action_bypass(ctx.guild, ctx.author, action_type):
                return True

            embed = discord.Embed(
                title="<:icon_cross:1372375094336425986> Access Denied",
                description="Antinuke is active on this server. Only Server Owner, Extraowners, or Whitelisted users can use this command!",
                color=0x000000
            )
            await ctx.send(embed=embed)
            return False
        except Exception:
            return True
    return commands.check(predicate)

"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""
