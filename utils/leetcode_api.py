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
from typing import Optional, Tuple, Dict
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
    
    # Retry configuration - INCREASED for better resilience
    MAX_RETRIES = 5  # Increased from 3
    BASE_DELAY = 2.0  # Increased from 1.0 seconds
    REQUEST_TIMEOUT = 15  # Increased from 10 seconds
    
    # Cache configuration
    CACHE_TTL = 86400  # 24 hours in seconds

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
        # In-memory cache: {slug: {"data": ProblemData, "timestamp": float}}
        self._metadata_cache: Dict[str, Dict] = {}

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
        # Clear cache on shutdown
        cache_size = len(self._metadata_cache)
        self._metadata_cache.clear()
        print(f"[LeetCode] Session closed and cache cleared ({cache_size} entries)")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics for monitoring"""
        total_entries = len(self._metadata_cache)
        current_time = time.time()
        fresh_entries = sum(1 for cached in self._metadata_cache.values() 
                           if current_time - cached["timestamp"] < self.CACHE_TTL)
        
        return {
            "total_cached": total_entries,
            "fresh_entries": fresh_entries,
            "cache_ttl_hours": self.CACHE_TTL / 3600,
            "oldest_entry_age": max((current_time - c["timestamp"] for c in self._metadata_cache.values()), default=0) / 60
        }

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
                    timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                ) as response:
                    # Success
                    if response.status == 200:
                        return await response.json()
                    
                    # Rate limited - wait and retry
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", base_delay * (2 ** attempt)))
                        response_text = await response.text()
                        print(f"[LeetCode] ⚠️ Rate limited (429). Waiting {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                        print(f"[LeetCode] Response preview: {response_text[:200]}")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Server error - retry with backoff
                    if response.status >= 500:
                        delay = base_delay * (2 ** attempt)
                        response_text = await response.text()
                        print(f"[LeetCode] ❌ Server error {response.status}. Retry in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        print(f"[LeetCode] Error response: {response_text[:200]}")
                        await asyncio.sleep(delay)
                        continue
                    
                    # Client error (4xx except 429) - don't retry
                    response_text = await response.text()
                    print(f"[LeetCode] ❌ Client error {response.status}. Not retrying.")
                    print(f"[LeetCode] Error details: {response_text[:300]}")
                    return None
                    
            except asyncio.TimeoutError:
                delay = base_delay * (2 ** attempt)
                print(f"[LeetCode] ⏱️ Timeout after {self.REQUEST_TIMEOUT}s. Retry {attempt + 1}/{max_retries} in {delay}s...")
                await asyncio.sleep(delay)
                
            except aiohttp.ClientError as e:
                delay = base_delay * (2 ** attempt)
                print(f"[LeetCode] 🌐 Network error: {type(e).__name__}: {e}. Retry in {delay}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
        
        print(f"[LeetCode] 🔴 All {max_retries} retries exhausted. API unavailable.")
        return None  # All retries exhausted

    # -----------------------------
    # Problem Metadata (with Caching)
    # -----------------------------

    async def get_problem_metadata(self, slug: str) -> Optional[ProblemData]:
        """
        Fetch canonical problem data from LeetCode with 24-hour caching.

        Used to:
        - Validate problem exists
        - Determine difficulty
        - Get canonical title
        
        Uses exponential backoff retry on failure.
        Cache reduces API calls by ~50% for repeated problem lookups.
        """
        try:
            # Check cache first
            if slug in self._metadata_cache:
                cached = self._metadata_cache[slug]
                age = time.time() - cached["timestamp"]
                if age < self.CACHE_TTL:
                    print(f"[LeetCode] Cache hit for {slug} (age: {age:.0f}s)")
                    return cached["data"]
                else:
                    # Expired, remove from cache
                    print(f"[LeetCode] Cache expired for {slug}")
                    del self._metadata_cache[slug]
            
            # Cache miss - fetch from API
            print(f"[LeetCode] Cache miss for {slug}, fetching from API...")
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

            result = ProblemData(
                question_id=question["questionId"],
                title=question["title"],
                title_slug=question["titleSlug"],
                difficulty=question["difficulty"]
            )
            
            # Store in cache
            self._metadata_cache[slug] = {
                "data": result,
                "timestamp": time.time()
            }
            print(f"[LeetCode] Cached metadata for {slug}")
            
            return result

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
