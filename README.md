# Discord DSA Bot

A Discord bot for daily DSA (Data Structures & Algorithms) problem tracking with support for multiple competitive programming platforms.

## Features

- **Daily Problem of the Day (POTD)** - Automated daily problem posting at midnight IST
- **Multi-Platform Support** - LeetCode, Codeforces, and GeeksforGeeks
- **Year-Based Difficulty** - Problems categorized by academic year (1st, 2nd, 3rd)
- **Submission Tracking** - Track user submissions with points and streaks
- **Leaderboards** - Weekly and monthly competitive leaderboards
- **Statistics Dashboard** - User stats and progress tracking
- **Problem Bank Queue** - Database-driven problem queue management

## Problem Display

Problems are displayed with full metadata:
- **LeetCode**: `Problem Title`
- **Codeforces**: `2013A - Problem Title` (includes problem ID)
- **GeeksforGeeks**: `Problem Title`

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/potd` | Get today's Problem of the Day |
| `/submit` | Submit a solved problem |
| `/stats` | View your statistics |
| `/leaderboard` | View the leaderboard |
| `/help` | Show available commands |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/setpotd` | Manually set a problem as POTD |
| `/removepotd` | Remove POTD status from a problem |
| `/clearpotd` | Clear all active POTDs |
| `/force_potd` | Trigger daily job immediately |
| `/preview_potd` | Preview next POTD without posting |
| `/scheduler_status` | Check scheduler status |
| `/check_permissions` | Check bot permissions in #potd channel |
| `/bulkaddproblems` | Add multiple problems from JSON file |
| `/problembank` | View problem queue status |

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database (Supabase recommended)
- Discord Bot Token

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd discord-dsa-bot
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Create `.env` file with required variables:
```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://user:password@host:port/database
```

4. Run the bot
```bash
python main.py
```

## Project Structure

```
discord-dsa-bot/
├── main.py                 # Bot entry point
├── config.py               # Configuration settings
├── keep_alive.py           # Web server for uptime monitoring
├── cogs/
│   ├── help_cog.py         # Help command
│   ├── leaderboard.py      # Leaderboard commands
│   ├── problems.py         # Problem management commands
│   ├── scheduler_cog.py    # Daily POTD scheduler
│   ├── stats_cog.py        # Statistics commands
│   ├── submission_cog.py   # Submission handling
│   └── user_mgmt.py        # User management
├── database/
│   ├── manager.py          # Database manager interface
│   ├── manager_supabase.py # Supabase/PostgreSQL implementation
│   └── schema_postgres.sql # Database schema
├── utils/
│   ├── logic.py            # Shared utility functions
│   ├── leetcode_api.py     # LeetCode API client
│   └── codeforces_api.py   # Codeforces API client
└── data/
    └── problem_bank.json   # Problem bank data
```

## Scheduler

The bot automatically posts daily problems at **12:00 AM IST** to the `#potd` channel. The scheduler:
- Pulls unused problems from the database queue
- Posts problems for Year 1, 2, and 3
- Pins the POTD message and unpins old ones
- Clears expired POTDs automatically

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Discord bot token |
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `COMMAND_PREFIX` | No | Bot command prefix (default: `!`) |

## Deployment

Deployed using Azure VM.

## License

MIT License
