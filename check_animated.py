import asyncio, os, discord
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TOKEN')

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    for g in client.guilds:
        anim_emojis = [e for e in g.emojis if e.animated]
        print(f'Guild: {g.name} | Animated emojis: {len(anim_emojis)}')
        for e in anim_emojis[:10]:
            print(f'  <a:{e.name}:{e.id}>')
    await client.close()

asyncio.run(client.start(token))
