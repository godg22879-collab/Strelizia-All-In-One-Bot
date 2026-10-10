import asyncio, os, discord, sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

TOKEN = os.getenv('TOKEN')
client = discord.Client(intents=discord.Intents.all())

async def test():
    await client.login(TOKEN)
    guilds = [g async for g in client.fetch_guilds()]
    print(f"Total guilds: {len(guilds)}")
    for g_entry in guilds:
        guild = await client.fetch_guild(g_entry.id)
        channels = await guild.fetch_channels()
        vcs = [c for c in channels if isinstance(c, discord.VoiceChannel)]
        print(f"Guild: {guild.name} (id={guild.id}), VCs: {len(vcs)}")
        if not vcs:
            continue
        for vc in vcs:
            print(f"  Testing VC: {vc.name} (id={vc.id})")
            # Try 1: channel.edit(status=...)
            try:
                await vc.edit(status="Testing channel.edit")
                print("  -> vc.edit(status=...) SUCCESS")
            except Exception as e:
                print(f"  -> vc.edit(status=...) ERROR: {type(e).__name__}: {e}")
            
            # Try 2: PUT /channels/{id}/voice-status with plain text
            try:
                res = await client.http.request(
                    discord.http.Route('PUT', '/channels/{channel_id}/voice-status', channel_id=vc.id),
                    json={'status': 'Testing plain status'}
                )
                print(f"  -> PUT /voice-status plain SUCCESS, res={res}")
            except Exception as e:
                print(f"  -> PUT /voice-status plain ERROR: {type(e).__name__}: {e}")

            # Try 3: PUT /channels/{id}/voice-status with custom animated emoji
            try:
                res = await client.http.request(
                    discord.http.Route('PUT', '/channels/{channel_id}/voice-status', channel_id=vc.id),
                    json={'status': '<a:vc_vinyl:1558068097674510356> Test with animated emoji'}
                )
                print(f"  -> PUT /voice-status with anim emoji SUCCESS, res={res}")
            except Exception as e:
                print(f"  -> PUT /voice-status with anim emoji ERROR: {type(e).__name__}: {e}")

            # Try 4: Check if discord.py has native vc.set_status or similar
            if hasattr(vc, 'set_status'):
                try:
                    await vc.set_status("Testing vc.set_status")
                    print("  -> vc.set_status SUCCESS")
                except Exception as e:
                    print(f"  -> vc.set_status ERROR: {e}")
            break
        break
    await client.close()

asyncio.run(test())
