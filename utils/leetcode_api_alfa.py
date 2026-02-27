"""
Alfa LeetCode API Wrapper
--------------------------
Uses the alfa-leetcode-api proxy service as a fallback/alternative
to direct LeetCode GraphQL API calls.

API: https://github.com/alfaarghya/alfa-leetcode-api
Endpoint: https://alfa-leetcode-api.onrender.com/
"""

import aiohttp
import time
from typing import Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class ProblemData:
    question_id: str
    title: str
    title_slug: str
    difficulty: str


class AlfaLeetCodeAPI:
    BASE_URL = "https://alfa-leetcode-api.onrender.com"
    
    # Cache configuration
    CACHE_TTL = 86400  # 24 hours in seconds
    REQUEST_TIMEOUT = 15  # seconds
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._metadata_cache: Dict[str, Dict] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        cache_size = len(self._metadata_cache)
        self._metadata_cache.clear()
        print(f"[AlfaLeetCode] Session closed and cache cleared ({cache_size} entries)")
    
    async def get_problem_metadata(self, slug: str) -> Optional[ProblemData]:
        """
        Fetch problem metadata using Alfa API.
        Endpoint: /select?titleSlug=<slug>
        """
        try:
            # Check cache first
            if slug in self._metadata_cache:
                cached = self._metadata_cache[slug]
                age = time.time() - cached["timestamp"]
                if age < self.CACHE_TTL:
                    print(f"[AlfaLeetCode] Cache hit for {slug} (age: {age:.0f}s)")
                    return cached["data"]
                else:
                    print(f"[AlfaLeetCode] Cache expired for {slug}")
                    del self._metadata_cache[slug]
            
            # Cache miss - fetch from API
            print(f"[AlfaLeetCode] Fetching metadata for: {slug}")
            session = await self._get_session()
            
            url = f"{self.BASE_URL}/select?titleSlug={slug}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)) as response:
                if response.status != 200:
                    print(f"[AlfaLeetCode] ❌ HTTP {response.status} for {slug}")
                    return None
                
                data = await response.json()
                
                # Check if problem exists
                if not data or "questionId" not in data:
                    print(f"[AlfaLeetCode] ❌ Problem not found: {slug}")
                    print(f"[AlfaLeetCode] Response: {data}")
                    return None
                
                # Map to our ProblemData structure (alfa API uses different field names)
                result = ProblemData(
                    question_id=str(data["questionId"]),
                    title=data["questionTitle"],  # ← FIXED: was "title", should be "questionTitle"
                    title_slug=data["titleSlug"],
                    difficulty=data["difficulty"]
                )
                
                # Cache the result
                self._metadata_cache[slug] = {
                    "data": result,
                    "timestamp": time.time()
                }
                print(f"[AlfaLeetCode] ✅ Found: {result.title} ({result.difficulty})")
                
                return result
                
        except Exception as e:
            print(f"[AlfaLeetCode] ❌ Error fetching metadata: {e}")
            return None
    
    async def verify_recent_submission(
        self,
        username: str,
        problem_slug: str,
        timeframe_minutes: int = 1440
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify user submission using Alfa API.
        Endpoint: /<username>/acSubmission?limit=20
        """
        try:
            print(f"[AlfaLeetCode] Verifying submission for user: {username}, problem: {problem_slug}")
            session = await self._get_session()
            
            url = f"{self.BASE_URL}/{username}/acSubmission?limit=20"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)) as response:
                if response.status == 404:
                    return False, "Invalid or private LeetCode profile."
                
                if response.status != 200:
                    print(f"[AlfaLeetCode] ❌ HTTP {response.status} for user {username}")
                    return False, f"API error: {response.status}"
                
                data = await response.json()
                
                # Debug: Log the response structure
                print(f"[AlfaLeetCode] Response type: {type(data)}")
                print(f"[AlfaLeetCode] Response: {str(data)[:200]}")
                
                # Handle different response formats
                if isinstance(data, dict):
                    if "error" in data:
                        return False, "Invalid or private LeetCode profile."
                    # If dict, extract submission list
                    submissions = data.get("submission", [])
                elif isinstance(data, list):
                    submissions = data
                else:
                    return False, "Unexpected API response format."
                
                if not submissions:
                    return False, "No public accepted submissions found."
                
                print(f"[AlfaLeetCode] Found {len(submissions)} recent submissions")
                
                # Check for matching problem
                now = time.time()
                max_age = timeframe_minutes * 60
                
                # Show first few slugs for debugging
                recent_slugs = [sub.get("titleSlug") for sub in submissions[:5]]
                print(f"[AlfaLeetCode] Recent problems: {recent_slugs}")
                
                for sub in submissions:
                    if sub.get("titleSlug") == problem_slug:
                        # Check timestamp if available
                        timestamp = sub.get("timestamp")
                        if timestamp:
                            submission_time = int(timestamp)
                            if now - submission_time <= max_age:
                                print(f"[AlfaLeetCode] ✅ Found matching submission for {problem_slug}")
                                return True, None
                        else:
                            # No timestamp, assume recent
                            print(f"[AlfaLeetCode] ✅ Found matching submission for {problem_slug} (no timestamp)")
                            return True, None
                
                return False, (
                    f"No accepted submission for `{problem_slug}` "
                    f"found in the last {timeframe_minutes / 60:.0f} hours."
                )
                
        except Exception as e:
            print(f"[AlfaLeetCode] ❌ Error verifying submission: {e}")
            return False, "Verification error. Please try again."
    
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
    
    async def test_api_health(self) -> Tuple[bool, str]:
        """Test if Alfa API is accessible"""
        try:
            print(f"[AlfaLeetCode] Testing API health...")
            result = await self.get_problem_metadata("two-sum")
            
            if result and result.title:
                return True, f"✅ Alfa API is healthy. Test problem '{result.title}' loaded successfully."
            else:
                return False, "❌ Alfa API returned empty response."
                
        except Exception as e:
            return False, f"❌ Alfa API test failed: {str(e)}"


# Singleton instance
_alfa_api: Optional[AlfaLeetCodeAPI] = None


def get_alfa_leetcode_api() -> AlfaLeetCodeAPI:
    global _alfa_api
    if _alfa_api is None:
        _alfa_api = AlfaLeetCodeAPI()
    return _alfa_api


async def close_alfa_leetcode_api():
    global _alfa_api
    if _alfa_api:
        await _alfa_api.close()
        _alfa_api = None
