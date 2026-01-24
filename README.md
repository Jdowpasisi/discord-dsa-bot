# 🤖 LeetCode Discord Bot

A feature-rich Discord bot for tracking LeetCode problem submissions, maintaining leaderboards, and encouraging consistent coding practice through streaks and gamification.

**Features**: Daily automated problems • Leaderboards • Streak tracking • Points system • Statistics • LeetCode API integration • Comprehensive validation

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Commands](#-commands)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [Database](#-database)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### Core Functionality
- ✅ **Slash Commands** - Modern Discord command interface with autocomplete
- ✅ **Problem Submissions** - Track completed LeetCode problems with `/leetcode_submit`
- ✅ **Real-time Validation** - Uses LeetCode GraphQL API to verify problems exist
- ✅ **Points System** - Earn points: Easy=10, Medium=20, Hard=40
- ✅ **Streaks** - Daily and weekly streak tracking with bonus points
- ✅ **User Statistics** - View personal stats with `/stats`

### Automated Features
- ✅ **Daily POTD** - Automated daily problem posting at midnight
- ✅ **Topic Rotation** - Weekly rotation through DSA topics (Arrays, Strings, etc.)
- ✅ **Sunday Revision** - Special Sunday problems from previous topics
- ✅ **Leaderboards** - Weekly & monthly leaderboards with automated posts
- ✅ **Duplicate Prevention** - Prevents re-submission of same problem within 30 days

### Advanced Features
- ✅ **Input Normalization** - Converts problem names automatically (e.g., "Two Sum" → "two-sum")
- ✅ **Cooldown System** - Rate limiting (1 submission per 30 seconds)
- ✅ **Channel Restrictions** - Commands only work in designated channels
- ✅ **Error Handling** - Comprehensive error messages and logging
- ✅ **State Persistence** - Scheduler state survives bot restarts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord.py 2.3.0+
- A Discord server and bot token

### 1-Minute Setup
```bash
# Clone repository
git clone https://github.com/yourusername/discord-dsa-bot.git
cd discord-dsa-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "DISCORD_TOKEN=your_token_here" > .env

# Run the bot
python bot.py
```

---

## 📦 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/discord-dsa-bot.git
cd discord-dsa-bot
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Discord token
# DISCORD_TOKEN=your_discord_bot_token_here
```

### Step 5: Create Discord Channels (Required)
Your server must have these channels:
- `#dsa` - For manual problem submissions
- `#potd` - For automated daily problems (POTD = Problem of the Day)

Ensure bot has permissions: View Channel, Send Messages, Embed Links, Read Message History

### Step 6: Run the Bot
```bash
python bot.py
```

**Expected output:**
```
✅ Bot is now ONLINE and ready!
👤 Logged in as: [BotName]
🌐 Connected to 1 guild(s): YourServer
✓ Successfully synced 4 slash command(s)
```

---

## 💬 Commands

### ⚡ Slash Commands (Primary Interface)

#### `/leetcode_submit`
Submit a completed LeetCode problem with difficulty auto-detected from LeetCode API.

**Usage:**
```
/leetcode_submit problem_name:two-sum
/leetcode_submit problem_name:Two Sum
```

**Parameters:**
- `problem_name` - Problem title or slug (required)

**Features:**
- 🟢 Auto-detects difficulty from LeetCode
- 🔒 Validates problem existence
- ⏱️ Rate limited (1 per 30 seconds)
- 🧮 Calculates points and streak bonuses
- 📊 Shows breakdown in response

**Restrictions:**
- ✅ Works in: `#dsa`, `#potd`
- ❌ Hidden in: Other channels

**Example Response:**
```
✅ Accepted!
Successfully submitted "Two Sum"

📝 Problem: Two Sum (#1)
⚡ Difficulty: Easy
💰 Points Earned: +10 points (base) + 5 bonus
🏆 Total Points: 150
🔥 Daily Streak: 5 days
📅 Weekly Streak: 2 weeks
```

---

#### `/stats`
View your statistics or another user's stats.

**Usage:**
```
/stats
/stats user:@John
```

**Shows:**
- 🏆 Total points (all-time)
- 📊 Global rank
- 🔥 Current daily streak
- 📅 Current weekly streak
- ⏰ Last submission date
- 📈 Problems submitted (count)

---

#### `/leaderboard`
View weekly or monthly leaderboards.

**Usage:**
```
/leaderboard
/leaderboard period:monthly
```

**Shows:**
- 🥇 Top 5 users with points
- 📊 Rank and streaks
- ⚠️ Inactive users (no submissions in 7 days)

---

#### `/help`
View all available commands and features.

---

### 🔧 Prefix Commands (Admin/Testing)

| Command | Purpose | Restriction |
|---------|---------|-------------|
| `!force_potd` | Manually trigger daily POTD | Owner only |
| `!post_now` | Trigger daily post | Admin |
| `!rotate_topic` | Advance to next topic | Admin |
| `!current_topic` | Show current topic | Public |
| `!scheduler_status` | Show scheduler stats | Admin |

---

## ⚙️ Configuration

Edit `config.py` to customize behavior:

```python
# Points per difficulty
POINTS_EASY = 10
POINTS_MEDIUM = 20
POINTS_HARD = 40

# Streak bonuses
DAILY_STREAK_BONUS = 5       # Extra points for daily streak
WEEKLY_STREAK_BONUS = 20     # Extra points for weekly streak

# Cooldown
SUBMISSION_COOLDOWN = 30     # Seconds between submissions

# Database
DATABASE_PATH = "data/leetcode_bot.db"

# Colors
COLOR_SUCCESS = discord.Color.green()
COLOR_ERROR = discord.Color.red()
COLOR_WARNING = discord.Color.orange()
```

---

## 🏗️ Architecture

### Project Structure
```
discord-dsa-bot/
├── 📄 bot.py                          # Main entry point
├── 📄 config.py                       # Configuration
├── 📄 requirements.txt                # Dependencies
├── 📄 .env.example                    # Environment template
│
├── 📁 cogs/                           # Command modules
│   ├── submission_cog.py              # /leetcode_submit command
│   ├── stats_cog.py                   # /stats, /leaderboard commands
│   ├── scheduler_cog.py               # Daily POTD automation
│   ├── help_cog.py                    # /help command
│   ├── problems.py                    # Problem management
│   └── leaderboard.py                 # Leaderboard utilities
│
├── 📁 database/                       # Database layer
│   ├── manager.py                     # DatabaseManager class
│   └── schema.sql                     # Database schema
│
├── 📁 data/                           # Data files
│   ├── problem_bank.json              # 6 topics × 10 problems
│   ├── scheduler_state.json           # Scheduler state
│   └── leetcode_bot.db                # SQLite database
│
└── 📁 utils/                          # Utilities
    ├── logic.py                       # Business logic
    └── leetcode_api.py                # LeetCode GraphQL client
```

### Data Flow

```
User Command (/leetcode_submit)
    ↓
SubmissionCog receives interaction
    ↓
Normalize problem name
    ↓
Query LeetCode API for problem details
    ↓
Validate submission (check for duplicates)
    ↓
Calculate points & bonuses
    ↓
Insert submission into database
    ↓
Update user stats
    ↓
Send response to user
```

---

## 📊 Database

### Schema Overview

**Users Table**
```sql
user_id: INTEGER PRIMARY KEY
total_points: INTEGER
daily_streak: INTEGER
weekly_streak: INTEGER
last_submission_date: DATE
last_week_submitted: TEXT
```

**Problems Table**
```sql
problem_slug: TEXT PRIMARY KEY
title: TEXT
difficulty: TEXT (Easy/Medium/Hard)
topic: TEXT
date_posted: DATE
```

**Submissions Table**
```sql
submission_id: INTEGER PRIMARY KEY AUTOINCREMENT
user_id: INTEGER FOREIGN KEY
problem_slug: TEXT FOREIGN KEY
submission_date: DATETIME
points_awarded: INTEGER
```

See [database/schema.sql](database/schema.sql) for full schema.

---

## 🧪 Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Commands

1. Create new file in `cogs/` (e.g., `cogs/myfeature_cog.py`)
2. Inherit from `commands.Cog`
3. Add command methods with `@app_commands.command()` or `@commands.command()`
4. Add `async def setup(bot)` at end of file
5. Bot auto-loads on startup

Example:
```python
from discord.ext import commands
from discord import app_commands

class MyFeatureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="mycommand")
    async def my_command(self, interaction):
        """My command description"""
        await interaction.response.send_message("Hello!")

async def setup(bot):
    await bot.add_cog(MyFeatureCog(bot))
```

---

## 🐛 Troubleshooting

### Bot Not Responding
**Check:**
1. Is bot online? (`!help` should work)
2. Are intents enabled? (Server Members, Message Content)
3. Check bot logs for errors
4. Verify bot has channel permissions

### Commands Not Appearing
**Solutions:**
1. Restart bot: `python bot.py`
2. Run `!sync` in Discord (owner only)
3. Clear Discord client cache
4. Check bot has "applications.commands" scope

### Submission Fails
**Common Issues:**
- Problem name incorrect → Use exact LeetCode name
- Wrong channel → Use `#dsa` or `#potd` only
- Rate limited → Wait 30+ seconds
- Problem doesn't exist on LeetCode → Verify on leetcode.com

### Daily POTD Not Posting
**Check:**
1. Bot is running (check logs)
2. `#potd` channel exists
3. Bot has Send Messages permission in `#potd`
4. Problem bank has problems: `data/problem_bank.json`
5. Use `!force_potd` to manually trigger

---

## 📖 Examples

### Example 1: Submit a Problem
```
User: /leetcode_submit problem_name:two-sum
Bot:  ✅ Accepted!
      Successfully submitted "Two Sum" (#1)
      ⚡ Difficulty: Easy
      💰 Points: +10
      🔥 Streak: 3 days
```

### Example 2: Check Leaderboard
```
User: /leaderboard
Bot:  Shows top 5 users with points, streaks, and rank
```

### Example 3: View Stats
```
User: /stats
Bot:  Shows your total points, rank, streaks, and last submission
```

---

## 🔐 Security & Best Practices

- ✅ Bot token stored in `.env` (never committed)
- ✅ Validation on all user inputs
- ✅ Rate limiting on submissions
- ✅ Database queries use parameterized statements
- ✅ Error messages don't leak sensitive info
- ✅ Logs include audit trail for admin commands

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 💡 Future Enhancements

- [ ] Difficulty filter for leaderboards
- [ ] Seasonal competitions
- [ ] Achievement badges
- [ ] Code submission storage
- [ ] Problem discussions
- [ ] Streak notifications
- [ ] Custom point multipliers per topic

---

## 📞 Support

Found a bug? Have a question?
- Open an [issue](https://github.com/yourusername/discord-dsa-bot/issues)
- Check existing documentation
- Review [Discord.py docs](https://discordpy.readthedocs.io/)

---

## 🎉 Acknowledgments

- Built with [Discord.py](https://github.com/Rapptz/discord.py)
- LeetCode API integration
- Community feedback and contributions

---

**Last Updated**: January 24, 2026  
**Status**: Production Ready ✅
