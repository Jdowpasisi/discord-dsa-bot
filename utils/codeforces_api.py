import aiohttp
import time
import re
from typing import Optional, Tuple, Dict, Any

class CodeforcesService:
    BASE_URL = "https://codeforces.com/api"

    async def get_recent_submissions(self, handle: str, count: int = 50):
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.BASE_URL}/user.status?handle={handle}&from=1&count={count}"
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    if data["status"] != "OK":
                        return None
                    return data["result"]
            except Exception as e:
                print(f"CF API Error: {e}")
                return None

    def parse_problem_id(self, problem_str: str) -> Tuple[Optional[int], Optional[str]]:
        """Parses '1872A' into (1872, 'A')"""
        match = re.match(r"^(\d+)([A-Z]\d?)$", problem_str.upper())
        if match:
            return int(match.group(1)), match.group(2)
        return None, None

    def get_difficulty_from_rating(self, rating: int) -> str:
        if rating <= 1200: return "Easy"
        if rating <= 1800: return "Medium"
        return "Hard"

    async def verify_submission(self, handle: str, problem_input: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verifies if a user solved a specific CF problem recently.
        Returns: (Verified, Message, Metadata)
        """
        contest_id, index = self.parse_problem_id(problem_input)
        if not contest_id:
            return False, "Invalid Codeforces Problem ID. Format example: 1872A", None

        submissions = await self.get_recent_submissions(handle)
        if submissions is None:
            return False, "Could not fetch Codeforces data. Check handle validity.", None

        # Check for accepted submission
        # Time window: Let's allow last 24 hours (86400 seconds)
        current_time = time.time()
        
        for sub in submissions:
            # Check Verdict
            if sub.get("verdict") != "OK":
                continue
            
            # Check Problem Match
            prob = sub.get("problem", {})
            if prob.get("contestId") == contest_id and prob.get("index") == index:
                
                # Check Time (24h window)
                sub_time = sub.get("creationTimeSeconds", 0)
                if (current_time - sub_time) > 86400:
                    return False, "Submission found, but it is older than 24 hours.", None

                # Success! Extract metadata
                rating = prob.get("rating", 1000) # Default to 1000 if unrated
                difficulty = self.get_difficulty_from_rating(rating)
                
                return True, "Verified", {
                    "title": f"{contest_id}{index} - {prob.get('name')}",
                    "difficulty": difficulty,
                    "url": f"https://codeforces.com/contest/{contest_id}/problem/{index}",
                    "platform": "Codeforces"
                }

        return False, "No accepted submission found in the last 24 hours.", None

# Singleton
_cf_service = CodeforcesService()
def get_codeforces_api():
    return _cf_service