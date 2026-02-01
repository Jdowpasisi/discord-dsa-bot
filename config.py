"""
Configuration file for LeetCode Discord Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
BOT_DESCRIPTION = "A Discord bot for tracking LeetCode problem submissions and maintaining leaderboards"

# Database Configuration - PostgreSQL/Supabase Only
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug: Show environment variable status (without exposing the full URL)
if DATABASE_URL:
    print(f"✓ DATABASE_URL found (length: {len(DATABASE_URL)} chars, starts with: {DATABASE_URL[:15]}...)")
else:
    print("⚠️  WARNING: DATABASE_URL environment variable is NOT set!")
    print("   Available environment variables:", list(os.environ.keys())[:10], "...")
    
if not DATABASE_URL or not DATABASE_URL.strip():
    raise ValueError(
        "\n" + "="*60 + "\n"
        "❌ DATABASE_URL environment variable is required but not set!\n"
        "="*60 + "\n"
        "This is likely a Render configuration issue.\n\n"
        "Fix in Render Dashboard:\n"
        "1. Go to your service in Render\n"
        "2. Click 'Environment' in the left sidebar\n"
        "3. Add a new environment variable:\n"
        "   Key:   DATABASE_URL\n"
        "   Value: postgresql://user:password@host:port/database\n"
        "4. Click 'Save Changes'\n"
        "5. Render will automatically redeploy\n\n"
        "Get your DATABASE_URL from Supabase:\n"
        "Settings -> Database -> Connection String -> URI\n"
        "="*60
    )

# Points System (No negative points ever)
POINTS = {
    "Easy": 5,
    "Medium": 10,
    "Hard": 15
}

# Streak Bonuses
DAILY_STREAK_BONUS = 5
WEEKLY_STREAK_BONUS = 20

# Bot Settings
LEADERBOARD_SIZE = 10
RECENT_SUBMISSIONS_LIMIT = 5

# Embed Colors (in hex)
COLOR_PRIMARY = 0x7289DA  # Discord Blurple
COLOR_SUCCESS = 0x00FF00  # Green
COLOR_ERROR = 0xFF0000    # Red
COLOR_INFO = 0x0099FF     # Blue
COLOR_WARNING = 0xFFAA00  # Orange
