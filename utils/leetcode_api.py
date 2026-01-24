"""
LeetCode API Helper
Queries the real LeetCode GraphQL API to verify problems and fetch metadata
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProblemData:
    """Data class for LeetCode problem information"""
    question_id: str
    title: str
    title_slug: str
    difficulty: str
    
    def __repr__(self):
        return f"ProblemData(id={self.question_id}, title='{self.title}', difficulty='{self.difficulty}')"


class LeetCodeAPI:
    """
    Client for interacting with LeetCode's GraphQL API
    
    Uses LeetCode's public GraphQL endpoint to verify problems and fetch metadata.
    This allows the bot to accept any valid LeetCode problem, not just those in the local database.
    """
    
    GRAPHQL_ENDPOINT = "https://leetcode.com/graphql"
    
    # GraphQL query to fetch problem data
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
    
    def __init__(self):
        """Initialize the LeetCode API client"""
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp session
        
        Returns:
            Active aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_problem_data(self, slug: str) -> Optional[ProblemData]:
        """
        Fetch problem data from LeetCode API
        
        Args:
            slug: Problem slug (e.g., "two-sum", "add-two-numbers")
        
        Returns:
            ProblemData object if problem exists, None if not found or error occurred
        
        Example:
            >>> api = LeetCodeAPI()
            >>> data = await api.get_problem_data("two-sum")
            >>> print(data.title)  # "Two Sum"
            >>> print(data.difficulty)  # "Easy"
            >>> await api.close()
        """
        try:
            session = await self._get_session()
            
            # Prepare GraphQL request
            payload = {
                "query": self.PROBLEM_QUERY,
                "variables": {
                    "titleSlug": slug
                }
            }
            
            # Make request to LeetCode GraphQL API (30 second timeout)
            async with session.post(self.GRAPHQL_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    print(f"LeetCode API returned status {response.status} for slug: {slug}")
                    return None
                
                data = await response.json()
                
                # Check if query returned data
                if "data" not in data or not data["data"]:
                    print(f"LeetCode API returned no data for slug: {slug}")
                    return None
                
                question = data["data"].get("question")
                
                # If question is None, the problem doesn't exist
                if question is None:
                    print(f"Problem not found on LeetCode: {slug}")
                    return None
                
                # Parse and return problem data
                return ProblemData(
                    question_id=question["questionId"],
                    title=question["title"],
                    title_slug=question["titleSlug"],
                    difficulty=question["difficulty"]
                )
        
        except aiohttp.ClientError as e:
            print(f"Network error while fetching problem '{slug}': {e}")
            return None
        
        except asyncio.TimeoutError:
            print(f"Timeout while fetching problem '{slug}' from LeetCode API")
            return None
        
        except KeyError as e:
            print(f"Unexpected response format from LeetCode API for '{slug}': {e}")
            return None
        
        except Exception as e:
            print(f"Unexpected error while fetching problem '{slug}': {e}")
            return None
    
    async def verify_problem(self, slug: str, expected_difficulty: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Verify if a problem exists and optionally check its difficulty
        
        Args:
            slug: Problem slug to verify
            expected_difficulty: If provided, verifies the difficulty matches (Easy, Medium, Hard)
        
        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if problem exists and passes all checks
            - (False, error_message) if problem doesn't exist or fails checks
        
        Example:
            >>> api = LeetCodeAPI()
            >>> valid, error = await api.verify_problem("two-sum", "Easy")
            >>> if valid:
            ...     print("Problem is valid!")
            >>> else:
            ...     print(f"Error: {error}")
        """
        problem_data = await self.get_problem_data(slug)
        
        if problem_data is None:
            return False, f"Problem `{slug}` not found on LeetCode. Please check the problem name/slug."
        
        # If expected difficulty is provided, verify it matches
        if expected_difficulty:
            if problem_data.difficulty != expected_difficulty:
                return False, (
                    f"Difficulty mismatch for `{problem_data.title}`:\n"
                    f"You submitted as: **{expected_difficulty}**\n"
                    f"Actual difficulty: **{problem_data.difficulty}**\n\n"
                    f"Please resubmit with the correct difficulty."
                )
        
        return True, None
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.session and not self.session.closed:
            # Note: This may not work in all cases due to event loop issues
            # It's better to explicitly call close() in an async context
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except:
                pass


# Singleton instance for reuse across the bot
_leetcode_api_instance: Optional[LeetCodeAPI] = None


def get_leetcode_api() -> LeetCodeAPI:
    """
    Get or create a singleton LeetCodeAPI instance
    
    Returns:
        Shared LeetCodeAPI instance
    
    Example:
        >>> api = get_leetcode_api()
        >>> problem = await api.get_problem_data("two-sum")
    """
    global _leetcode_api_instance
    if _leetcode_api_instance is None:
        _leetcode_api_instance = LeetCodeAPI()
    return _leetcode_api_instance


async def close_leetcode_api():
    """
    Close the singleton LeetCodeAPI instance
    
    Call this when shutting down the bot to clean up resources.
    
    Example:
        >>> await close_leetcode_api()
    """
    global _leetcode_api_instance
    if _leetcode_api_instance is not None:
        await _leetcode_api_instance.close()
        _leetcode_api_instance = None
