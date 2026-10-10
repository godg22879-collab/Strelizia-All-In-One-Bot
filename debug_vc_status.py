"""Debug VC status setting — test all methods."""
import asyncio, os, discord
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    # Find a VC we're in or any VC
    for guild in client.guilds:
        for vc in guild.voice_channels:
            print(f'  VC: {vc.name} (id={vc.id}) in {guild.name}')
            # Try method 1: channel.edit(status=...)
            try:
                await vc.edit(status='<a:vc_note1:1558068093316505620> Test Status')
                print(f'  -> channel.edit(status=...) SUCCESS on {vc.name}')
            except Exception as e:
                print(f'  -> channel.edit(status=...) FAILED: {e}')

            # Try method 2: raw HTTP PUT /channels/{id}/voice-status
            try:
                await client.http.request(
                    discord.http.Route('PUT', '/channels/{channel_id}/voice-status', channel_id=vc.id),
                    json={'status': '<a:vc_vinyl:1558068097674510356> Test Status 2'}
                )
                print(f'  -> PUT /voice-status SUCCESS on {vc.name}')
            except Exception as e:
                print(f'  -> PUT /voice-status FAILED: {e}')
            break
        break
    await client.close()

asyncio.run(client.start(TOKEN))
