import os
import re
import asyncio
import aiohttp
import zipfile
from pathlib import Path

# Search directories
SEARCH_DIRS = ['AeroX', 'Music Emojis']
OUTPUT_DIR = Path('downloaded_default_emojis')
ZIP_FILE = Path('default_bot_emojis.zip')

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

emoji_regex = re.compile(r'<(a?):([A-Za-z0-9_~-]+):([0-9]{15,22})>')
found = {}

for sdir in SEARCH_DIRS:
    for root, dirs, files in os.walk(sdir):
        for f in files:
            if f.endswith(('.py', '.json', '.env', '.txt', '.md')):
                path = os.path.join(root, f)
                try:
                    with open(path, encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                    matches = emoji_regex.findall(content)
                    for animated, name, eid in matches:
                        is_anim = bool(animated)
                        if eid not in found:
                            found[eid] = {
                                'name': name,
                                'animated': is_anim,
                                'count': 1
                            }
                        else:
                            found[eid]['count'] += 1
                            if is_anim:
                                found[eid]['animated'] = True
                except Exception:
                    pass

print(f"Total unique default emojis discovered: {len(found)}")

async def download_emoji(session, eid, data, semaphore):
    name = re.sub(r'[^A-Za-z0-9_-]', '_', data['name'])
    ext = 'gif' if data['animated'] else 'png'
    filename = f"{name}_{eid}.{ext}"
    filepath = OUTPUT_DIR / filename
    
    # Discord CDN URL
    url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}?size=128&quality=lossless"
    
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    filepath.write_bytes(content)
                    return True, filename
                elif ext == 'gif':
                    # Try png fallback if gif fails
                    png_url = f"https://cdn.discordapp.com/emojis/{eid}.png?size=128&quality=lossless"
                    async with session.get(png_url, timeout=aiohttp.ClientTimeout(total=10)) as r2:
                        if r2.status == 200:
                            content = await r2.read()
                            filename = f"{name}_{eid}.png"
                            (OUTPUT_DIR / filename).write_bytes(content)
                            return True, filename
                elif ext == 'png':
                    # Try gif fallback if png fails
                    gif_url = f"https://cdn.discordapp.com/emojis/{eid}.gif?size=128&quality=lossless"
                    async with session.get(gif_url, timeout=aiohttp.ClientTimeout(total=10)) as r3:
                        if r3.status == 200:
                            content = await r3.read()
                            filename = f"{name}_{eid}.gif"
                            (OUTPUT_DIR / filename).write_bytes(content)
                            return True, filename
                print(f"Failed {filename}: HTTP {resp.status}")
                return False, filename
        except Exception as e:
            print(f"Error {filename}: {e}")
            return False, filename

async def main():
    semaphore = asyncio.Semaphore(15)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [download_emoji(session, eid, data, semaphore) for eid, data in found.items()]
        results = await asyncio.gather(*tasks)
        
    downloaded = [fn for ok, fn in results if ok]
    print(f"Successfully downloaded {len(downloaded)} / {len(found)} emojis to {OUTPUT_DIR.resolve()}")
    
    # Create ZIP file
    with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in OUTPUT_DIR.glob('*.*'):
            zipf.write(file, arcname=file.name)
            
    print(f"Created ZIP archive: {ZIP_FILE.resolve()} ({ZIP_FILE.stat().st_size / 1024:.1f} KB)")

if __name__ == '__main__':
    asyncio.run(main())
