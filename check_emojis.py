import asyncio, os, aiohttp
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TOKEN')
app_id = '1546186345838411917'

async def main():
    headers = {'Authorization': f'Bot {token}'}
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://discord.com/api/v10/applications/{app_id}/emojis', headers=headers) as r:
            data = await r.json()
    emojis = data.get('items', [])
    print(f'Total app emojis: {len(emojis)}')
    for e in emojis:
        animated = e.get('animated', False)
        tag = '(animated) ' if animated else ''
        fmt = f'<a:{e["name"]}:{e["id"]}>' if animated else f'<:{e["name"]}:{e["id"]}>'
        print(f'  {tag}{fmt}')

asyncio.run(main())
