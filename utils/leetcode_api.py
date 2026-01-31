"""
LeetCode Service
----------------
Unified service for:
1. Fetching problem metadata (title, difficulty)
2. Verifying user submissions via recent accepted solutions

This replaces:
- leetcode_api.py (metadata only)
- ai_studio_code.py (submission verification)

Used by the Discord bot for automatic verification.
"""

import asyncio
import aiohttp
import time
from typing import Optional, Tuple
from dataclasses import dataclass


# -----------------------------
# Data Models
# -----------------------------

@dataclass
class ProblemData:
    question_id: str
    title: str
    title_slug: str
    difficulty: str


# -----------------------------
# LeetCode Service
# -----------------------------

class LeetCodeService:
    GRAPHQL_ENDPOINT = "https://leetcode.com/graphql"
    
    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

    PROBLEM_QUERY = """
    query questionData($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionId
            title
            titleSlug
            difficulty
        }
    }
    """

    RECENT_SUBMISSIONS_QUERY = """
    query recentAcSubmissionList($username: String!, $limit: Int!) {
        recentAcSubmissionList(username: $username, limit: $limit) {
            titleSlug
            timestamp
        }
    }
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DiscordBot/LeetCodeVerifier/1.0"
                }
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # -----------------------------
    # Retry Logic with Exponential Backoff
    # -----------------------------

    async def _request_with_retry(
        self,
        payload: dict,
        max_retries: int = None,
        base_delay: float = None
    ) -> Optional[dict]:
        """
        Makes a request with automatic retry on failure.
        
        Exponential backoff: 1s → 2s → 4s (doubles each retry)
        Handles: Rate limits (429), Server errors (5xx), Timeouts
        """
        max_retries = max_retries or self.MAX_RETRIES
        base_delay = base_delay or self.BASE_DELAY
        session = await self._get_session()
        
        for attempt in range(max_retries):
            try:
                async with session.post(
                    self.GRAPHQL_ENDPOINT,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    # Success
                    if response.status == 200:
                        return await response.json()
                    
                    # Rate limited - wait and retry
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", base_delay * (2 ** attempt)))
                        print(f"[LeetCode] Rate limited. Waiting {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Server error - retry with backoff
                    if response.status >= 500:
                        delay = base_delay * (2 ** attempt)
                        print(f"[LeetCode] Server error {response.status}. Retry in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                    # Client error (4xx except 429) - don't retry
                    print(f"[LeetCode] Client error {response.status}. Not retrying.")
                    return None
                    
            except asyncio.TimeoutError:
                delay = base_delay * (2 ** attempt)
                print(f"[LeetCode] Timeout. Retry {attempt + 1}/{max_retries} in {delay}s...")
                await asyncio.sleep(delay)
                
            except aiohttp.ClientError as e:
                delay = base_delay * (2 ** attempt)
                print(f"[LeetCode] Network error: {e}. Retry in {delay}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
        
        print(f"[LeetCode] All {max_retries} retries exhausted.")
        return None  # All retries exhausted

    # -----------------------------
    # Problem Metadata
    # -----------------------------

    async def get_problem_metadata(self, slug: str) -> Optional[ProblemData]:
        """
        Fetch canonical problem data from LeetCode.

        Used to:
        - Validate problem exists
        - Determine difficulty
        - Get canonical title
        
        Uses exponential backoff retry on failure.
        """
        try:
            payload = {
                "query": self.PROBLEM_QUERY,
                "variables": {"titleSlug": slug}
            }

            data = await self._request_with_retry(payload)
            
            if not data:
                return None

            question = data.get("data", {}).get("question")
            if not question:
                return None

            return ProblemData(
                question_id=question["questionId"],
                title=question["title"],
                title_slug=question["titleSlug"],
                difficulty=question["difficulty"]
            )

        except Exception as e:
            print(f"[LeetCodeService] Metadata error: {e}")
            return None

    # -----------------------------
    # Submission Verification
    # -----------------------------

    async def verify_recent_submission(
        self,
        username: str,
        problem_slug: str,
        timeframe_minutes: int = 1440
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify whether a user solved a problem recently.

        Default timeframe = 24 hours (daily challenge friendly)
        Uses exponential backoff retry on failure.
        """
        try:
            payload = {
                "query": self.RECENT_SUBMISSIONS_QUERY,
                "variables": {"username": username, "limit": 20}
            }

            data = await self._request_with_retry(payload)
            
            if not data:
                return False, "LeetCode API unavailable after multiple retries."

            if "errors" in data:
                return False, "Invalid or private LeetCode profile."

            submissions = data.get("data", {}).get("recentAcSubmissionList", [])
            if not submissions:
                return False, "No public accepted submissions found."

            now = time.time()
            max_age = timeframe_minutes * 60

            for sub in submissions:
                if sub["titleSlug"] == problem_slug:
                    submission_time = int(sub["timestamp"])
                    if now - submission_time <= max_age:
                        return True, None

            return False, (
                f"No accepted submission for `{problem_slug}` "
                f"found in the last {timeframe_minutes / 60} hours."
            )

        except Exception as e:
            print(f"[LeetCodeService] Submission verification error: {e}")
            return False, "Internal verification error."


# -----------------------------
# Singleton Access
# -----------------------------

_leetcode_service: Optional[LeetCodeService] = None


def get_leetcode_api() -> LeetCodeService:
    global _leetcode_service
    if _leetcode_service is None:
        _leetcode_service = LeetCodeService()
    return _leetcode_service


async def close_leetcode_api():
    global _leetcode_service
    if _leetcode_service:
        await _leetcode_service.close()
        _leetcode_service = None
