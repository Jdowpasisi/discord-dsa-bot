"""
LeetCode API Client using Playwright Browser Automation
Bypasses Cloudflare and bot detection by using a real browser
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime, timedelta

# Browser automation will be imported only when needed
_browser = None
_browser_context = None
_page = None


@dataclass
class ProblemData:
    """Container for LeetCode problem metadata"""
    title: str
    title_slug: str
    difficulty: str
    


class PlaywrightLeetCodeAPI:
    """LeetCode API using Playwright for browser automation"""
    
    CACHE_TTL = 24 * 3600  # 24 hours in seconds
    
    def __init__(self):
        self._metadata_cache = {}
        self._browser_initialized = False
    
    async def _ensure_browser(self):
        """Initialize browser if not already done"""
        global _browser, _browser_context, _page
        
        if not self._browser_initialized:
            try:
                from playwright.async_api import async_playwright
                
                print("[Browser] Initializing Playwright browser...")
                self._playwright = await async_playwright().start()
                
                # Use chromium with stealth settings
                _browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                # Create context with realistic browser fingerprint
                _browser_context = await _browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Set extra headers
                await _browser_context.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'application/json, text/plain, */*'
                })
                
                _page = await _browser_context.new_page()
                
                # Remove automation indicators
                await _page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                self._browser_initialized = True
                print("[Browser] ✅ Browser initialized successfully")
                
            except ImportError:
                print("[Browser] ❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
                raise
            except Exception as e:
                print(f"[Browser] ❌ Failed to initialize browser: {e}")
                raise
    
    async def close(self):
        """Close browser and clean up resources"""
        global _browser, _browser_context, _page
        
        if _browser:
            try:
                await _browser.close()
                await self._playwright.stop()
                _browser = None
                _browser_context = None
                _page = None
                self._browser_initialized = False
                print("[Browser] Browser closed")
            except Exception as e:
                print(f"[Browser] Error closing browser: {e}")
        
        self._metadata_cache.clear()
    
    async def get_problem_metadata(self, slug: str) -> Optional[ProblemData]:
        """
        Fetch problem metadata using browser automation
        
        Args:
            slug: Problem slug (e.g., "two-sum")
            
        Returns:
            ProblemData object or None if problem not found
        """
        # Check cache first
        if slug in self._metadata_cache:
            cached_data, timestamp = self._metadata_cache[slug]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self.CACHE_TTL:
                print(f"[Browser] Cache hit for {slug} (age: {age:.0f}s)")
                return cached_data
            else:
                print(f"[Browser] Cache expired for {slug}")
                del self._metadata_cache[slug]
        
        try:
            await self._ensure_browser()
            
            print(f"[Browser] Fetching metadata for: {slug}")
            
            url = f"https://leetcode.com/problems/{slug}/"
            
            # Navigate to problem page
            response = await _page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response.status == 404:
                print(f"[Browser] ❌ Problem not found: {slug}")
                return None
            
            # Wait for the problem content to load
            try:
                # Wait for difficulty badge or title
                await _page.wait_for_selector('[class*="text-difficulty"]', timeout=10000)
            except Exception:
                # Might be behind Cloudflare challenge, wait a bit more
                await asyncio.sleep(3)
            
            # Extract problem data using JavaScript
            problem_data = await _page.evaluate("""
                () => {
                    // Get title from h1 or meta tag
                    const titleElement = document.querySelector('div[data-cy="question-title"]') || 
                                       document.querySelector('h1') ||
                                       document.querySelector('meta[property="og:title"]');
                    let title = '';
                    if (titleElement) {
                        title = titleElement.getAttribute('content') || titleElement.textContent;
                        // Remove problem number prefix like "1. "
                        title = title.replace(/^\d+\.\s*/, '').trim();
                    }
                    
                    // Get difficulty
                    const difficultyElement = document.querySelector('[class*="text-difficulty"]') ||
                                            document.querySelector('[diff]');
                    let difficulty = 'Medium'; // default
                    if (difficultyElement) {
                        const text = difficultyElement.textContent.trim();
                        if (text.includes('Easy')) difficulty = 'Easy';
                        else if (text.includes('Medium')) difficulty = 'Medium';
                        else if (text.includes('Hard')) difficulty = 'Hard';
                    }
                    
                    return {
                        title: title,
                        difficulty: difficulty
                    };
                }
            """)
            
            if not problem_data.get('title'):
                print(f"[Browser] ⚠️ Could not extract title for {slug}, using slug")
                problem_data['title'] = slug.replace('-', ' ').title()
            
            result = ProblemData(
                title=problem_data['title'],
                title_slug=slug,
                difficulty=problem_data['difficulty']
            )
            
            # Cache the result
            self._metadata_cache[slug] = (result, datetime.now())
            print(f"[Browser] ✅ Found: {result.title} ({result.difficulty})")
            
            return result
            
        except Exception as e:
            print(f"[Browser] ❌ Error fetching metadata: {e}")
            return None
    
    async def verify_recent_submission(
        self, 
        username: str, 
        problem_slug: str, 
        timeframe_minutes: int = 1440
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify if user has solved the problem recently
        
        Args:
            username: LeetCode username
            problem_slug: Problem slug to verify
            timeframe_minutes: Time window in minutes (default 24h)
            
        Returns:
            Tuple of (verified: bool, error_message: Optional[str])
        """
        try:
            await self._ensure_browser()
            
            print(f"[Browser] Verifying submission for {username}: {problem_slug}")
            
            # Navigate to user's recent submissions page
            url = f"https://leetcode.com/{username}/"
            response = await _page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response.status == 404:
                return False, f"User '{username}' not found on LeetCode"
            
            # Wait for profile content
            await asyncio.sleep(2)
            
            # Click on "Recent AC" or submissions tab if exists
            try:
                # Try to find and click recent submissions
                submissions_tab = await _page.query_selector('button:has-text("Recent AC"), a:has-text("Recent")')
                if submissions_tab:
                    await submissions_tab.click()
                    await asyncio.sleep(1)
            except Exception:
                pass  # Tab might not exist or already visible
            
            # Extract recent solved problems
            recent_problems = await _page.evaluate("""
                (problemSlug) => {
                    const links = Array.from(document.querySelectorAll('a[href*="/problems/"]'));
                    const problems = links.map(link => {
                        const href = link.getAttribute('href');
                        const match = href.match(/\\/problems\\/([^\\/]+)/);
                        return match ? match[1] : null;
                    }).filter(Boolean);
                    
                    // Check if our problem is in the list
                    return {
                        found: problems.includes(problemSlug),
                        recentProblems: problems.slice(0, 20)
                    };
                }
            """, problem_slug)
            
            if recent_problems['found']:
                print(f"[Browser] ✅ Found matching submission for {problem_slug}")
                return True, None
            else:
                print(f"[Browser] Recent problems: {recent_problems['recentProblems'][:5]}")
                return False, f"No recent submission found for '{problem_slug}' in last {timeframe_minutes // 60} hours"
                
        except Exception as e:
            print(f"[Browser] ❌ Error verifying submission: {e}")
            return False, f"Verification failed: {str(e)}"


# Global instance management
_api_instance = None

def get_browser_leetcode_api() -> PlaywrightLeetCodeAPI:
    """Get or create the global browser API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = PlaywrightLeetCodeAPI()
    return _api_instance

async def close_browser_leetcode_api():
    """Close the browser API and clean up resources"""
    global _api_instance
    if _api_instance is not None:
        await _api_instance.close()
        _api_instance = None
