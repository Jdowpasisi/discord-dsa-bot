"""
Core Business Logic for LeetCode Discord Bot
Handles scoring, validation, streaks, and problem name normalization
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from enum import Enum
from utils.leetcode_api import get_leetcode_api


# ==========================
# Enums & Constants
# ==========================

class SubmissionStatus(Enum):
    VALID = "valid"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    NOT_LINKED = "not_linked"

class Difficulty(Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

DIFFICULTY_POINTS = {
    "Easy": 10,
    "Medium": 20,
    "Hard": 40,
    "1st Year": 10, 
    "2nd Year": 20,
    "3rd Year": 40
}


# ==========================
# Normalization & Helpers
# ==========================

def normalize_problem_name(name: str) -> str:
    if not name: return ""
    return name.lower().replace(" ", "-").strip("-")

def calculate_points(difficulty: str, is_duplicate: bool = False) -> int:
    if is_duplicate: return 0
    return DIFFICULTY_POINTS.get(difficulty, 0)

def validate_difficulty(difficulty: str) -> bool:
    return difficulty in DIFFICULTY_POINTS

def get_week_bounds(date: datetime) -> Tuple[datetime, datetime]:
    start = date - timedelta(days=date.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


# ==========================
# Submission Validation
# ==========================

async def validate_submission(
    db_manager,
    user_id: int,
    raw_problem_name: str,
    difficulty: Optional[str] = None,
    current_date: Optional[datetime] = None
) -> Tuple[SubmissionStatus, str, Optional[Dict[str, Any]]]:

    if current_date is None: current_date = datetime.now()
    problem_slug = normalize_problem_name(raw_problem_name)

    user_profile = await db_manager.get_user(user_id)
    if not user_profile or not user_profile.get("leetcode_username"):
        return (SubmissionStatus.NOT_LINKED, "⚠️ Link your account with `/setup` first.", None)

    leetcode_username = user_profile["leetcode_username"]
    api = get_leetcode_api()

    # 1. Metadata Check
    problem_data = await api.get_problem_metadata(problem_slug)
    if not problem_data:
        return (SubmissionStatus.INVALID, f"❌ Problem `{problem_slug}` not found.", None)

    # 2. Verification Check (24h)
    verified, error = await api.verify_recent_submission(leetcode_username, problem_slug, timeframe_minutes=1440)
    if not verified:
        return (SubmissionStatus.INVALID, f"❌ Verification failed: {error}", None)

    # 3. Duplicate Check
    if await db_manager.check_duplicate_submission(user_id, problem_slug):
        return (SubmissionStatus.DUPLICATE, f"Already submitted `{problem_data.title}`.", None)

    points = calculate_points(problem_data.difficulty)

    return (
        SubmissionStatus.VALID,
        "✅ Verified!",
        {
            "problem_slug": problem_slug,
            "title": problem_data.title,
            "difficulty": problem_data.difficulty,
            "points": points,
            "question_id": problem_data.question_id
        }
    )


# ==========================
# Streak Logic (FIXED)
# ==========================

def calculate_streaks(
    user_data: Dict[str, Any],
    current_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculates streaks based on DB state. 
    Returns updated counts and the formatted strings to save back to DB.
    """
    if current_date is None:
        current_date = datetime.now()

    today = current_date.date()
    
    # ISO Calendar: (Year, Week, Day). Use this for consistent week tracking.
    iso_cal = current_date.isocalendar()
    # Format: "2025-W04" (Ensures strict string matching)
    current_week_str = f"{iso_cal.year}-W{iso_cal.week:02d}"

    daily_streak = user_data.get("daily_streak", 0)
    weekly_streak = user_data.get("weekly_streak", 0)
    
    last_date_raw = user_data.get("last_submission_date")
    last_week_str = user_data.get("last_week_submitted")

    streak_maintained = False
    new_week_event = False

    # ---- Daily Streak Logic ----
    if last_date_raw:
        try:
            # Handle potential full timestamp "YYYY-MM-DDTHH:MM:SS" by taking just date
            last_date = datetime.fromisoformat(last_date_raw).date()
            diff = (today - last_date).days

            if diff == 0:
                # Already submitted today
                streak_maintained = True
            elif diff == 1:
                # Submitted yesterday
                daily_streak += 1
            else:
                # Skipped a day
                daily_streak = 1
        except ValueError:
            daily_streak = 1
    else:
        # First ever submission
        daily_streak = 1

    # ---- Weekly Streak Logic ----
    if not last_week_str:
        weekly_streak = 1
        new_week_event = True
    elif last_week_str == current_week_str:
        # Already submitted this week -> No change
        pass
    else:
        # It's a different week string. Is it the *next* week?
        # Parse "YYYY-W04"
        try:
            l_year, l_week_part = last_week_str.split("-W")
            l_year, l_week = int(l_year), int(l_week_part)
            c_year, c_week = iso_cal.year, iso_cal.week
            
            is_consecutive = False
            
            if c_year == l_year and c_week == l_week + 1:
                is_consecutive = True
            # Handle Year Rollover (Week 52/53 -> Week 1)
            elif c_year == l_year + 1 and c_week == 1 and l_week >= 52:
                is_consecutive = True
                
            if is_consecutive:
                weekly_streak += 1
            else:
                weekly_streak = 1
            
            new_week_event = True
        except ValueError:
            # Malformed string in DB, reset
            weekly_streak = 1
            new_week_event = True

    return {
        "daily_streak": daily_streak,
        "weekly_streak": weekly_streak,
        "streak_maintained": streak_maintained,
        "new_week": new_week_event,
        # RETURN THE FORMATTED STRINGS FOR DB SAVING
        "db_date": current_date.isoformat(),
        "db_week": current_week_str
    }

def format_streak_message(daily: int, weekly: int) -> str:
    return f"🔥 {daily} Day{'s' if daily!=1 else ''} | 📅 {weekly} Week{'s' if weekly!=1 else ''}"