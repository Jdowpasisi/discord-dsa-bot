# Utility functions and helpers
from .logic import (
    normalize_problem_name,
    validate_submission,
    calculate_streaks,
    calculate_points,
    format_streak_message,
    validate_difficulty,
    get_week_bounds,
    SubmissionStatus,
    Difficulty,
    DIFFICULTY_POINTS
)

from .leetcode_api import (
    LeetCodeService,
    ProblemData,
    get_leetcode_api,
    close_leetcode_api,
)

__all__ = [
    'normalize_problem_name',
    'validate_submission',
    'calculate_streaks',
    'calculate_points',
    'format_streak_message',
    'validate_difficulty',
    'get_week_bounds',
    'SubmissionStatus',
    'Difficulty',
    'DIFFICULTY_POINTS',
    'LeetCodeService',
    'ProblemData',
    'get_leetcode_api',
    'close_leetcode_api',
]
