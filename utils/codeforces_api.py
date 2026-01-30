import aiohttp
import time
import re
from typing import Optional, Tuple, Dict, Any

class CodeforcesService:
    BASE_URL = "https://codeforces.com/api"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            # ✅ FIX: Add User-Agent to bypass Cloudflare 521/403 blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    def parse_problem_id(self, problem_str: str) -> Tuple[Optional[int], Optional[str]]:
        """Parses '1872A' into (1872, 'A')"""
        # Remove spaces, uppercase
        clean = problem_str.strip().upper()
        # Match Number followed by Letter(s) (e.g., 282A, 123C2)
        match = re.match(r"^(\d+)([A-Z]\d?)$", clean)
        if match:
            return int(match.group(1)), match.group(2)
        return None, None
    def get_difficulty_from_rating(self, rating: int) -> str:
        if rating <= 1200: return "Easy"
        if rating <= 1800: return "Medium"
        return "Hard"

    def generate_url(self, contest_id, index):
        """Generates the correct Contest URL"""
        return f"https://codeforces.com/contest/{contest_id}/problem/{index}"

    async def get_problem_metadata(self, problem_id: str) -> Optional[Dict]:
        """Fetches metadata for a CF problem using Contest API (Lighter)."""
        contest_id, index = self.parse_problem_id(problem_id)
        if not contest_id:
            print(f"[CF] Invalid ID format: {problem_id}")
            return None

        session = await self._get_session()
        try:
            # Fetch specific contest info instead of global problemset
            url = f"{self.BASE_URL}/contest.standings?contestId={contest_id}&from=1&count=1"
            print(f"[CF] Fetching: {url}")
            
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"[CF] API Status: {resp.status}")
                    return None
                
                data = await resp.json()
                if data["status"] != "OK":
                    print(f"[CF] API Error: {data.get('comment', 'Unknown error')}")
                    return None
                
                # The 'problems' list contains all problems for that contest
                problems = data.get("result", {}).get("problems", [])
                
                for p in problems:
                    if p.get("index") == index:
                        rating = p.get("rating", 1000)
                        return {
                            "slug": f"{contest_id}{index}",
                            "title": p.get("name"),
                            "difficulty": self.get_difficulty_from_rating(rating),
                            "url": self.generate_url(contest_id, index),
                            "platform": "Codeforces"
                        }
                print(f"[CF] Problem {index} not found in contest {contest_id}")
        except Exception as e:
            print(f"[CF] Metadata Error: {e}")
            return None
        return None

    async def get_recent_submissions(self, handle: str, count: int = 50):
        session = await self._get_session()
        try:
            url = f"{self.BASE_URL}/user.status?handle={handle}&from=1&count={count}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"[CF] Submissions API Status: {resp.status}")
                    return None
                data = await resp.json()
                if data["status"] != "OK": return None
                return data["result"]
        except Exception as e:
            print(f"[CF] API Error: {e}")
            return None

    async def verify_submission(self, handle: str, problem_input: str) -> Tuple[bool, str, Optional[Dict]]:
        contest_id, index = self.parse_problem_id(problem_input)
        if not contest_id:
            return False, "Invalid Codeforces Problem ID. Format example: 1872A", None

        submissions = await self.get_recent_submissions(handle)
        if submissions is None:
            return False, "Could not fetch Codeforces data. Check handle validity or try again later.", None

        current_time = time.time()
        
        for sub in submissions:
            if sub.get("verdict") != "OK": continue
            
            prob = sub.get("problem", {})
            if prob.get("contestId") == contest_id and prob.get("index") == index:
                
                sub_time = sub.get("creationTimeSeconds", 0)
                if (current_time - sub_time) > 86400:
                    return False, "Submission found, but it is older than 24 hours.", None

                rating = prob.get("rating", 1000)
                difficulty = self.get_difficulty_from_rating(rating)
                
                return True, "Verified", {
                    "title": prob.get('name'),
                    "difficulty": difficulty,
                    "url": self.generate_url(contest_id, index), # ✅ Correct URL
                    "platform": "Codeforces",
                    "slug": f"{contest_id}{index}"
                }

        return False, "No accepted submission found in the last 24 hours.", None

_cf_service = None
def get_codeforces_api():
    global _cf_service
    if _cf_service is None:
        _cf_service = CodeforcesService()
    return _cf_service