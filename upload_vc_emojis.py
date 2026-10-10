"""Upload the 4 animated GIF emojis to Discord Application Emojis endpoint."""
import asyncio, os, aiohttp, base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
APP_ID = '1546186345838411917'
GIF_DIR = Path(r"C:\Users\Administrator\.gemini\antigravity-ide\brain\920b6c02-b8fd-4736-b8dc-305dd36e05b7\vc_emojis")

EMOJIS = [
    ("vc_note1", GIF_DIR / "vc_note1.gif"),
    ("vc_note2", GIF_DIR / "vc_note2.gif"),
    ("vc_vinyl", GIF_DIR / "vc_vinyl.gif"),
    ("vc_phones", GIF_DIR / "vc_phones.gif"),
]

async def upload():
    headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}
    url = f'https://discord.com/api/v10/applications/{APP_ID}/emojis'

    async with aiohttp.ClientSession() as session:
        # First delete old vc_ emojis if they exist
        async with session.get(url, headers=headers) as r:
            data = await r.json()
        existing = {e['name']: e['id'] for e in data.get('items', [])}
        for name in ['vc_note1', 'vc_note2', 'vc_vinyl', 'vc_phones']:
            if name in existing:
                del_url = f'{url}/{existing[name]}'
                await session.delete(del_url, headers=headers)
                print(f'Deleted old: {name}')

        # Upload new animated GIFs
        for name, path in EMOJIS:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode()
            payload = {"name": name, "image": f"data:image/gif;base64,{b64}"}
            async with session.post(url, headers=headers, json=payload) as r:
                resp = await r.json()
                if 'id' in resp:
                    animated = resp.get('animated', False)
                    tag = f"<a:{name}:{resp['id']}>" if animated else f"<:{name}:{resp['id']}>"
                    print(f"Uploaded: {tag}  (animated={animated})")
                else:
                    print(f"FAILED {name}: {resp}")

asyncio.run(upload())
