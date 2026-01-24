"""
Core Business Logic for LeetCode Discord Bot
Handles scoring, validation, streaks, and problem name normalization
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from enum import Enum
from utils.leetcode_api import get_leetcode_api


# ============ Scoring Constants ============

class Difficulty(Enum):
    """Problem difficulty levels"""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


# Points awarded per difficulty level (no negative points ever)
DIFFICULTY_POINTS = {
    Difficulty.EASY: 10,
    Difficulty.MEDIUM: 20,
    Difficulty.HARD: 40,
    "Easy": 10,
    "Medium": 20,
    "Hard": 40
}


class SubmissionStatus(Enum):
    """Possible submission validation statuses"""
    VALID = "valid"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    NOT_TODAY = "not_today"


# ============ Input Normalization ============

def normalize_problem_name(name: str) -> str:
    """
    Normalize problem name to standard slug format.
    
    Converts to lowercase and replaces spaces with hyphens.
    Example: "Two Sum" -> "two-sum"
    
    Args:
        name: Problem name in any format
        
    Returns:
        Normalized problem slug in lowercase with hyphens
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Replace spaces with hyphens
    normalized = normalized.replace(" ", "-")
    
    # Remove multiple consecutive hyphens
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    
    # Strip leading/trailing hyphens
    normalized = normalized.strip("-")
    
    return normalized


# ============ Submission Validation ============

async def validate_submission(
    db_manager,
    user_id: int,
    problem_slug: str,
    difficulty: Optional[str] = None,
    current_date: datetime = None
) -> Tuple[SubmissionStatus, str, Optional[Dict[str, Any]]]:
    """
    Validate a problem submission against LeetCode API.
    
    Checks:
    1. Problem exists on LeetCode (via GraphQL API)
    2. User hasn't already solved this problem (idempotency check)
    
    Args:
        db_manager: DatabaseManager instance
        user_id: Discord user ID
        problem_slug: Normalized problem slug
        difficulty: Optional - Problem difficulty (Easy, Medium, Hard).
                   If None, will be fetched from LeetCode API.
        current_date: Current date (defaults to now)
        
    Returns:
        Tuple of (SubmissionStatus, message, problem_data_dict)
        problem_data_dict contains: {"difficulty": str, "title": str, "points": int}
        or None if validation failed
    """
    if current_date is None:
        current_date = datetime.now()
    
    # Normalize problem slug
    problem_slug = normalize_problem_name(problem_slug)
    
    # ============ STEP 1: VERIFY WITH LEETCODE API ============
    api = get_leetcode_api()
    
    try:
        problem_data = await api.get_problem_data(problem_slug)
    except Exception as e:
        # API error - graceful degradation
        return (
            SubmissionStatus.INVALID,
            f"⚠️ LeetCode API error: {str(e)}\n"
            f"Please try again in a moment. If the problem persists, LeetCode might be experiencing issues.",
            None
        )
    
    if problem_data is None:
        # Problem doesn't exist on LeetCode
        return (
            SubmissionStatus.INVALID,
            f"❌ Problem `{problem_slug}` not found on LeetCode.\n"
            f"Please check the problem name and try again.",
            None
        )
    
    # Use API's difficulty (this is the real difficulty from LeetCode)
    real_difficulty = problem_data.difficulty
    real_title = problem_data.title
    
    # If user provided difficulty, validate it matches
    if difficulty and difficulty != real_difficulty:
        return (
            SubmissionStatus.INVALID,
            f"⚠️ Difficulty mismatch for '{real_title}':\n"
            f"You specified: **{difficulty}**\n"
            f"Actual difficulty: **{real_difficulty}**\n"
            f"Please resubmit with the correct difficulty.",
            None
        )
    
    # ============ STEP 2: CHECK FOR DUPLICATE ============
    has_submitted = await db_manager.check_duplicate_submission(user_id, problem_slug)
    
    if has_submitted:
        return (
            SubmissionStatus.DUPLICATE,
            f"You've already submitted `{problem_slug}`. Duplicate submissions earn 0 points.",
            None
        )
    
    # ============ VALIDATION PASSED ============
    # Calculate points based on real difficulty
    points = calculate_points(real_difficulty, is_duplicate=False)
    
    return (
        SubmissionStatus.VALID,
        "Submission is valid!",
        {
            "difficulty": real_difficulty,
            "title": real_title,
            "points": points,
            "question_id": problem_data.question_id
        }
    )


# ============ Streak Logic ============

def calculate_streaks(
    user_data: Dict[str, Any],
    current_date: datetime = None
) -> Dict[str, Any]:
    """
    Calculate daily and weekly streaks for a user.
    
    Daily Streak Rules:
    - Increment if last_submission_date was yesterday
    - Reset to 1 if skipped (more than 1 day ago)
    - Maintain current streak if already submitted today
    
    Weekly Streak Rules:
    - Increment if user has submitted >= 1 solution during the current
      Monday-Sunday week (independent of daily streak)
    - Track by week number (YYYY-WW format)
    
    Args:
        user_data: Dictionary with user information including:
            - last_submission_date: ISO format timestamp or None
            - last_week_submitted: Week string (YYYY-WW) or None
            - daily_streak: Current daily streak count
            - weekly_streak: Current weekly streak count
        current_date: Current datetime (defaults to now)
        
    Returns:
        Dictionary with updated streak information:
            - daily_streak: Updated daily streak count
            - weekly_streak: Updated weekly streak count
            - streak_maintained: Boolean indicating if this is a new submission today
    """
    if current_date is None:
        current_date = datetime.now()
    
    today = current_date.date()
    current_week = current_date.strftime("%Y-%W")  # ISO week number
    
    # Get current streak values (default to 0 if not set)
    daily_streak = user_data.get("daily_streak", 0)
    weekly_streak = user_data.get("weekly_streak", 0)
    last_submission_date_str = user_data.get("last_submission_date")
    last_week_submitted = user_data.get("last_week_submitted")
    
    # ============ Daily Streak Calculation ============
    
    if last_submission_date_str:
        # Parse the last submission date
        try:
            last_submission_date = datetime.fromisoformat(last_submission_date_str).date()
        except (ValueError, TypeError):
            # Invalid date format, treat as no previous submission
            last_submission_date = None
    else:
        last_submission_date = None
    
    streak_maintained = False
    
    if last_submission_date:
        days_diff = (today - last_submission_date).days
        
        if days_diff == 0:
            # Already submitted today - maintain current streak
            # Don't increment, just keep the current value
            streak_maintained = True
            # daily_streak stays the same
            
        elif days_diff == 1:
            # Submitted yesterday - increment streak
            daily_streak += 1
            
        else:
            # Skipped one or more days - reset to 1
            daily_streak = 1
    else:
        # First submission ever
        daily_streak = 1
    
    # ============ Weekly Streak Calculation ============
    
    if last_week_submitted:
        if current_week == last_week_submitted:
            # Same week - maintain current weekly streak
            # weekly_streak stays the same
            pass
        else:
            # New week - increment weekly streak
            # Check if it's the next consecutive week
            try:
                # Parse last week (YYYY-WW)
                last_year, last_week_num = map(int, last_week_submitted.split("-"))
                curr_year, curr_week_num = map(int, current_week.split("-"))
                
                # Simple consecutive week check
                # (This is simplified; proper week arithmetic is complex with year boundaries)
                if (curr_year == last_year and curr_week_num == last_week_num + 1) or \
                   (curr_year == last_year + 1 and curr_week_num == 1 and last_week_num >= 52):
                    # Consecutive week - increment
                    weekly_streak += 1
                else:
                    # Non-consecutive week - reset to 1
                    weekly_streak = 1
            except (ValueError, AttributeError):
                # Error parsing week - reset to 1
                weekly_streak = 1
    else:
        # First week ever
        weekly_streak = 1
    
    return {
        "daily_streak": daily_streak,
        "weekly_streak": weekly_streak,
        "streak_maintained": streak_maintained,
        "new_week": last_week_submitted != current_week if last_week_submitted else True
    }


# ============ Points Calculation ============

def calculate_points(difficulty: str, is_duplicate: bool = False) -> int:
    """
    Calculate points for a submission.
    
    Args:
        difficulty: Problem difficulty (Easy, Medium, Hard)
        is_duplicate: Whether this is a duplicate submission
        
    Returns:
        Points to award (0 if duplicate, difficulty points otherwise)
        Never returns negative points.
    """
    if is_duplicate:
        return 0
    
    points = DIFFICULTY_POINTS.get(difficulty, 0)
    
    # Ensure no negative points
    return max(0, points)


# ============ Helper Functions ============

def get_week_bounds(date: datetime) -> Tuple[datetime, datetime]:
    """
    Get the start and end of the week (Monday-Sunday) for a given date.
    
    Args:
        date: Any datetime within the week
        
    Returns:
        Tuple of (week_start, week_end) as datetime objects
    """
    # Get Monday of the current week (weekday 0 = Monday)
    week_start = date - timedelta(days=date.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get Sunday of the current week
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def format_streak_message(daily_streak: int, weekly_streak: int) -> str:
    """
    Format a user-friendly streak message.
    
    Args:
        daily_streak: Number of consecutive days
        weekly_streak: Number of consecutive weeks
        
    Returns:
        Formatted string with streak information
    """
    daily_msg = f"🔥 {daily_streak} day{'s' if daily_streak != 1 else ''}"
    weekly_msg = f"📅 {weekly_streak} week{'s' if weekly_streak != 1 else ''}"
    
    return f"{daily_msg} | {weekly_msg}"


def validate_difficulty(difficulty: str) -> bool:
    """
    Validate if a difficulty string is valid.
    
    Args:
        difficulty: Difficulty string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return difficulty in ["Easy", "Medium", "Hard"]
