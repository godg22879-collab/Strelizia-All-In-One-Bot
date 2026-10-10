import os 
from dotenv import load_dotenv 

load_dotenv()
TOKEN = os.environ.get("TOKEN") or os.environ.get("DISCORD_TOKEN")
NAME ="D4Hz"
server ="https://discord.gg/JxCFmz9nZP"
ch ="https://discord.com/channels/1324668335069331477/1324668336470102143"
owner_env = os.environ.get("OWNER_IDS", "")
OWNER_IDS = [int(i.strip()) for i in owner_env.split(",") if i.strip().isdigit()] if owner_env else [1124248109472550993, 1366749025814052895, 1198187445859139595]
BotName ="D4Hz"
serverLink ="https://discord.gg/JxCFmz9nZP"
"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""
