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

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/leetcode_bot.db")

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
