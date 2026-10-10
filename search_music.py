import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('AeroX/cogs/commands/music.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

keywords = ['disc', 'NOW PLAYING', 'set_vc_status', 'vc_status', 'display_player_embed']
for i, line in enumerate(lines, 1):
    l = line.lower()
    if any(k.lower() in l for k in keywords):
        print(f'Line {i}: {line.rstrip()[:150]}')
