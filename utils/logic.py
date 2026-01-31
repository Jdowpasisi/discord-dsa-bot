"""
Core Business Logic for LeetCode Discord Bot
Handles scoring, validation, streaks, and problem name normalization
"""
from utils.codeforces_api import get_codeforces_api
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
    "Medium": 10,
    "Hard": 15,
    "1st Year": 10, 
    "2nd Year": 10,
    "3rd Year": 15
}


# ==========================
# Normalization & Helpers
# ==========================

def normalize_problem_name(name: str) -> str:
    if not name: return ""
    return name.lower().replace(" ", "-").strip("-")

def parse_gfg_slug(input_str: str) -> str:
    """
    Extract slug from GFG URL or return cleaned slug.
    
    Examples:
        'https://www.geeksforgeeks.org/problems/detect-cycle/1' -> 'detect-cycle'
        'detect-cycle' -> 'detect-cycle'
        'Detect Cycle' -> 'detect-cycle'
    """
    import re
    
    # Try to extract slug from URL pattern
    gfg_url_pattern = r"https?://(?:www\.)?geeksforgeeks\.org/problems/([^/]+)/?.*"
    match = re.match(gfg_url_pattern, input_str.strip())
    
    if match:
        return match.group(1)
    else:
        # Not a URL, normalize it as a slug
        return normalize_problem_name(input_str)

def generate_gfg_title(slug: str) -> str:
    """
    Generate readable title from GFG slug.
    
    Example: 'detect-cycle' -> 'Detect Cycle'
    """
    import re
    # Replace hyphens with spaces and title case
    title = slug.replace("-", " ").title()
    # Remove trailing numbers (e.g., 'Problem 1' at end)
    clean_title = re.sub(r'\s+\d+$', '', title).strip()
    return clean_title if clean_title else title

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
    platform: str = "LeetCode",
    current_date: Optional[datetime] = None
) -> Tuple[SubmissionStatus, str, Optional[Dict[str, Any]]]:

    if current_date is None: current_date = datetime.now()
    
    # Normalize input based on platform expectations
    # LeetCode/GFG use slugs (lowercase, hyphens)
    # Codeforces uses Contest+Index (e.g. 1872A), logic handles parsing later
    if platform != "Codeforces":
        problem_id = normalize_problem_name(raw_problem_name)
    else:
        problem_id = raw_problem_name.upper().strip() # Keep CF IDs uppercase (e.g. 1872A)

    # 1. Get User Profile
    user_profile = await db_manager.get_user(user_id)
    if not user_profile:
        return (SubmissionStatus.NOT_LINKED, "⚠️ User not found. Run `/setup` first.", None)

    submission_data = {}

    # ==========================
    # Platform: LeetCode
    # ==========================
    if platform == "LeetCode":
        if not user_profile.get("leetcode_username"):
            return (SubmissionStatus.NOT_LINKED, "⚠️ Link your LeetCode account first using `/setup leetcode:<your_username>`", None)
        
        leetcode_username = user_profile["leetcode_username"]
        api = get_leetcode_api()

        # Fetch Metadata
        problem_data = await api.get_problem_metadata(problem_id)
        if not problem_data:
            return (SubmissionStatus.INVALID, f"❌ Problem `{problem_id}` not found on LeetCode.", None)

        # Verify Submission (24h window)
        verified, error = await api.verify_recent_submission(leetcode_username, problem_id, timeframe_minutes=1440)
        if not verified:
            return (SubmissionStatus.INVALID, f"❌ Verification failed: {error}", None)

        # ✅ FIX: Use title_slug consistently as the problem identifier
        submission_data = {
            "title": problem_data.title,
            "difficulty": problem_data.difficulty,
            "url": f"https://leetcode.com/problems/{problem_data.title_slug}/",
            "slug": problem_data.title_slug  # ← CHANGED: Use slug instead of question_id
        }

    # ==========================
    # Platform: Codeforces
    # ==========================
    elif platform == "Codeforces":
        if not user_profile.get("codeforces_handle"):
            return (SubmissionStatus.NOT_LINKED, "⚠️ Link your Codeforces account first using `/setup codeforces:<your_handle>`", None)
            
        cf_api = get_codeforces_api()
        verified, msg, meta = await cf_api.verify_submission(user_profile["codeforces_handle"], problem_id)
        
        if not verified:
            return (SubmissionStatus.INVALID, f"❌ {msg}", None)
            
        submission_data = {
            "title": meta["title"],
            "difficulty": meta["difficulty"],
            "url": meta["url"],
            "slug": problem_id  # ← CHANGED: Use consistent key name
        }

    # ==========================
    # Platform: GeeksforGeeks
    # ==========================
    elif platform == "GeeksforGeeks":
        if not user_profile.get("gfg_handle"):
            return (SubmissionStatus.NOT_LINKED, "⚠️ Link your GFG account first using `/setup geeksforgeeks:<your_handle>`", None)
            
        # ✅ FIX: Normalize GFG input (URL or slug) to consistent slug
        clean_slug = parse_gfg_slug(raw_problem_name)
        readable_title = generate_gfg_title(clean_slug)
        problem_url = f"https://www.geeksforgeeks.org/problems/{clean_slug}/"
        
        # Trust-Based Validation
        submission_data = {
            "title": readable_title,  # ✅ Readable title, not raw URL
            "difficulty": "Easy",     # GFG always Easy
            "url": problem_url,       # Canonical URL
            "slug": clean_slug        # ✅ Normalized slug for duplicate detection
        }

    else:
        return (SubmissionStatus.INVALID, "❌ Unknown Platform selected.", None)

    # ==========================
    # Common Logic (Duplicate Check & Points)
    # ==========================
    
    # ✅ FIX: Use consistent slug key
    db_slug = submission_data["slug"]

    # Check for duplicates in DB
    if await db_manager.check_duplicate_submission(user_id, db_slug, platform):
        return (SubmissionStatus.DUPLICATE, f"Already submitted `{submission_data['title']}`.", None)

    # Calculate Points
    points = calculate_points(submission_data["difficulty"])

    return (
        SubmissionStatus.VALID,
        "✅ Verified!",
        {
            "problem_slug": db_slug,  # ← This is now consistently the slug
            "title": submission_data["title"],
            "difficulty": submission_data["difficulty"],
            "points": points,
            "platform": platform,
            "url": submission_data["url"]
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


# ==========================
# URL Generation
# ==========================

def generate_problem_url(platform: str, slug: str) -> str:
    """
    Generate the correct problem URL for any platform.
    
    Args:
        platform: "LeetCode", "Codeforces", or "GeeksforGeeks"
        slug: Problem identifier (e.g., "two-sum", "1872A", "detect-cycle")
    
    Returns:
        Full URL to the problem page
    
    Examples:
        generate_problem_url("LeetCode", "two-sum") 
            -> "https://leetcode.com/problems/two-sum/"
        generate_problem_url("Codeforces", "1872A") 
            -> "https://codeforces.com/contest/1872/problem/A"
        generate_problem_url("GeeksforGeeks", "detect-cycle") 
            -> "https://www.geeksforgeeks.org/problems/detect-cycle/"
    """
    import re
    
    if platform == "LeetCode":
        return f"https://leetcode.com/problems/{slug}/"
    
    elif platform == "Codeforces":
        # Parse contest ID and problem letter from formats like "1872A" or "1872A1"
        match = re.match(r"^(\d+)([A-Z]\d?)$", slug.upper())
        if match:
            contest_id = match.group(1)
            problem_letter = match.group(2)
            return f"https://codeforces.com/contest/{contest_id}/problem/{problem_letter}"
        else:
            # Fallback: problemset format (shouldn't normally reach here)
            return f"https://codeforces.com/problemset/problem/{slug}"
    
    elif platform == "GeeksforGeeks":
        # If it's already a full URL, return as-is
        if slug.startswith("http"):
            return slug
        return f"https://www.geeksforgeeks.org/problems/{slug}/"
    
    else:
        # Unknown platform fallback
        return slug