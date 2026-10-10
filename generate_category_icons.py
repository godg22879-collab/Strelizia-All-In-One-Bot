import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.abspath("assets/category_icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CATEGORIES = [
    {"id": "antinuke", "name": "Security", "color": (255, 75, 75)},
    {"id": "automod", "name": "Automod", "color": (255, 140, 50)},
    {"id": "bypass", "name": "Bypass", "color": (255, 215, 0)},
    {"id": "moderation", "name": "Moderation", "color": (230, 45, 90)},
    {"id": "general", "name": "General", "color": (0, 210, 255)},
    {"id": "music", "name": "Music", "color": (245, 80, 180)},
    {"id": "voice", "name": "Voice", "color": (80, 160, 255)},
    {"id": "welcome", "name": "Welcomer", "color": (40, 225, 180)},
    {"id": "ticket", "name": "Ticket", "color": (255, 190, 60)},
    {"id": "giveaway", "name": "Giveaway", "color": (255, 105, 180)},
    {"id": "server", "name": "Server Config", "color": (180, 200, 220)},
    {"id": "backup", "name": "Backup", "color": (100, 180, 255)},
    {"id": "logging", "name": "Logging", "color": (50, 215, 120)},
    {"id": "booster", "name": "Boost Nitro", "color": (255, 115, 250)},
    {"id": "ai", "name": "AI System", "color": (170, 110, 255)},
    {"id": "games", "name": "Games", "color": (120, 255, 100)},
    {"id": "fun", "name": "Fun", "color": (255, 165, 90)},
    {"id": "leveling", "name": "Leveling", "color": (255, 210, 60)},
    {"id": "roleplay", "name": "Roleplay", "color": (255, 130, 170)},
    {"id": "crew", "name": "Staff / Crew", "color": (255, 215, 80)},
    {"id": "verification", "name": "Verification", "color": (0, 230, 220)},
    {"id": "sticky", "name": "Sticky", "color": (255, 230, 70)},
    {"id": "counting", "name": "Counting", "color": (100, 210, 255)},
    {"id": "tracking", "name": "Tracking", "color": (255, 90, 90)},
    {"id": "ignore", "name": "Ignore", "color": (170, 170, 190)},
    {"id": "ytverify", "name": "YT Verify", "color": (255, 50, 50)},
    {"id": "utility", "name": "Utility", "color": (140, 190, 255)},
]

print(f"Total categories configured: {len(CATEGORIES)}")
