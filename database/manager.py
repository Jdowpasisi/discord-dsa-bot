"""
Database Manager for LeetCode Discord Bot - Supabase/PostgreSQL Version
Handles database connections, initialization, and common queries using asyncpg
"""

import asyncpg
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database operations for the Discord bot (Supabase compatible)"""
    
    def __init__(self, database_url: str):
        """
        Initialize the DatabaseManager
        
        Args:
            database_url: PostgreSQL connection URL (from Supabase)
                         Format: postgresql://user:password@host:port/database
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self) -> None:
        """Establish database connection pool with retry logic"""
        import asyncio
        
        max_retries = 5  # Increased for Supabase wake-up time
        retry_delay = 10  # Increased to allow Supabase to wake up
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"   Connection attempt {attempt}/{max_retries} to: {self.database_url[:30]}...")
                
                # Create connection pool for Supabase/pgBouncer compatibility
                # pgBouncer requires minimal connection settings
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=3,
                    command_timeout=60,
                    statement_cache_size=0  # Critical: Disable prepared statements for pgBouncer
                )
                print(f"✓ Database connected (PostgreSQL/Supabase)")
                return  # Success!
            except asyncpg.InvalidCatalogNameError as e:
                print(f"✗ Database connection failed: Invalid database name")
                print(f"   Check that your DATABASE_URL points to the correct database")
                raise  # Don't retry on auth errors
            except asyncpg.InvalidPasswordError as e:
                print(f"✗ Database connection failed: Invalid password")
                print(f"   Check that your password in DATABASE_URL is correct")
                raise  # Don't retry on auth errors
            except asyncpg.exceptions.InternalServerError as e:
                error_msg = str(e)
                if "Connection to database not available" in error_msg or "Authentication query failed" in error_msg:
                    print(f"✗ Connection attempt {attempt} failed: Supabase database is paused or unavailable")
                    if attempt < max_retries:
                        print(f"   ⏳ Waking up Supabase project... (this may take 30-60 seconds)")
                        print(f"   Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        print(f"\n✗ Supabase database is not responding after {max_retries} attempts")
                        print(f"   📝 ACTION REQUIRED:")
                        print(f"   1. Go to https://supabase.com/dashboard")
                        print(f"   2. Click on your project")
                        print(f"   3. Check if project is paused (free tier pauses after ~7 days of inactivity)")
                        print(f"   4. Click 'Resume' or 'Restore' if paused")
                        print(f"   5. Wait 30-60 seconds for the database to wake up")
                        print(f"   6. Try running the bot again")
                        raise
                else:
                    print(f"✗ Database internal server error: {e}")
                    raise
            except (TimeoutError, OSError, ConnectionRefusedError) as e:
                print(f"✗ Connection attempt {attempt} failed: {type(e).__name__}")
                if attempt < max_retries:
                    print(f"   Retrying in {retry_delay} seconds... (Supabase may be waking up)")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    print(f"\n✗ All {max_retries} connection attempts failed")
                    print(f"   Possible causes:")
                    print(f"   1. Supabase project is paused (check dashboard)")
                    print(f"   2. Incorrect host/port in DATABASE_URL")
                    print(f"   3. Network/firewall blocking connection")
                    print(f"   4. Invalid connection string format")
                    raise
            except Exception as e:
                print(f"✗ Database connection failed: {e}")
                print(f"   Error type: {type(e).__name__}")
                if attempt < max_retries:
                    print(f"   Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise
        
    async def close(self) -> None:
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("✓ Database connection closed")
            
    async def initialize_tables(self) -> None:
        """Create database tables from schema_postgres.sql if they don't exist"""
        if not self.pool:
            raise RuntimeError("Database not connected. Call connect() first.")
            
        schema_path = Path(__file__).parent / "schema_postgres.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
        # Read the schema file
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Split into individual statements and execute separately
        # This is required for pgBouncer compatibility (Supabase)
        statements = []
        current_statement = []
        
        for line in schema_sql.split('\n'):
            # Skip comments and empty lines
            stripped = line.strip()
            if stripped.startswith('--') or not stripped:
                continue
            
            current_statement.append(line)
            
            # Check if statement is complete (ends with semicolon)
            if stripped.endswith(';'):
                statement = '\n'.join(current_statement).strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # Execute each statement separately
        async with self.pool.acquire() as conn:
            for statement in statements:
                try:
                    await conn.execute(statement)
                except Exception as e:
                    # Log but continue - table might already exist
                    logger.debug(f"Schema execution note: {e}")
        
        print("✓ Database tables initialized")
    
    # ============ Helper Methods ============
    
    def _row_to_dict(self, row: asyncpg.Record, keys: List[str]) -> Dict[str, Any]:
        """Convert asyncpg Record to dictionary"""
        if row is None:
            return None
        return {key: row[i] for i, key in enumerate(keys)}
        
    # ============ User Management Methods ============
    
    async def get_user(self, discord_id: int) -> Optional[dict]:
        """
        Get user information by Discord ID
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            Dictionary with user data or None if not found
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT discord_id, total_points, daily_streak, weekly_streak,
                          last_submission_date, last_week_submitted, student_year,
                          leetcode_username, codeforces_handle, gfg_handle
                   FROM Users WHERE discord_id = $1""",
                discord_id
            )
            if row:
                return {
                    "discord_id": row[0],
                    "total_points": row[1],
                    "daily_streak": row[2],
                    "weekly_streak": row[3],
                    "last_submission_date": row[4],
                    "last_week_submitted": row[5],
                    "student_year": row[6],
                    "leetcode_username": row[7],
                    "codeforces_handle": row[8],
                    "gfg_handle": row[9]
                }
        return None
        
    async def create_user(self, discord_id: int) -> None:
        """
        Create a new user in the database
        
        Args:
            discord_id: Discord user ID
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO Users (discord_id) VALUES ($1)
                   ON CONFLICT (discord_id) DO NOTHING""",
                discord_id
            )
    
    async def check_handle_exists(self, handle_type: str, handle_value: str, exclude_discord_id: int = None) -> bool:
        """
        Check if a handle (leetcode_username, codeforces_handle, etc.) is already in use.
        
        Args:
            handle_type: Column name ('leetcode_username', 'codeforces_handle', 'gfg_handle')
            handle_value: The handle to check
            exclude_discord_id: Exclude this user from the check (for updates)
            
        Returns:
            True if handle exists (taken by another user), False otherwise
        """
        async with self.pool.acquire() as conn:
            if exclude_discord_id:
                row = await conn.fetchrow(
                    f"SELECT discord_id FROM Users WHERE {handle_type} = $1 AND discord_id != $2",
                    handle_value, exclude_discord_id
                )
            else:
                row = await conn.fetchrow(
                    f"SELECT discord_id FROM Users WHERE {handle_type} = $1",
                    handle_value
                )
            return row is not None
    
    async def delete_user(self, discord_id: int) -> None:
        """
        Delete a user and all their submissions from the database.
        
        Args:
            discord_id: Discord user ID to delete
        """
        async with self.pool.acquire() as conn:
            # Delete submissions first (foreign key constraint)
            await conn.execute("DELETE FROM Submissions WHERE discord_id = $1", discord_id)
            # Delete user
            await conn.execute("DELETE FROM Users WHERE discord_id = $1", discord_id)
        
    async def update_user_profile(
        self, 
        discord_id: int, 
        student_year: str = None, 
        leetcode_username: str = None, 
        codeforces_handle: str = None, 
        gfg_handle: str = None
    ) -> None:
        """
        Update user profile information
        
        Args:
            discord_id: Discord user ID
            student_year: Student year level (1, 2, 3, 4, or General)
            leetcode_username: LeetCode username
            codeforces_handle: Codeforces handle
            gfg_handle: GeeksforGeeks handle
        """
        updates = []
        params = []
        param_idx = 1
        
        if student_year is not None:
            updates.append(f"student_year = ${param_idx}")
            params.append(student_year)
            param_idx += 1
            
        if leetcode_username is not None:
            updates.append(f"leetcode_username = ${param_idx}")
            params.append(leetcode_username)
            param_idx += 1
        
        if codeforces_handle is not None:
            updates.append(f"codeforces_handle = ${param_idx}")
            params.append(codeforces_handle)
            param_idx += 1
            
        if gfg_handle is not None:
            updates.append(f"gfg_handle = ${param_idx}")
            params.append(gfg_handle)
            param_idx += 1
                
        if updates:
            params.append(discord_id)
            query = f"UPDATE Users SET {', '.join(updates)} WHERE discord_id = ${param_idx}"
            async with self.pool.acquire() as conn:
                await conn.execute(query, *params)
        
    async def update_user_points(self, discord_id: int, points_to_add: int) -> None:
        """
        Update user's total points
        
        Args:
            discord_id: Discord user ID
            points_to_add: Points to add to user's total
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE Users SET total_points = total_points + $1 WHERE discord_id = $2",
                points_to_add, discord_id
            )
        
    async def update_user_streaks(
        self, 
        discord_id: int, 
        daily_streak: int, 
        weekly_streak: int,
        last_submission_date: str,
        last_week_submitted: str
    ) -> None:
        """
        Update user's streak information
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE Users 
                   SET daily_streak = $1, 
                       weekly_streak = $2, 
                       last_submission_date = $3,
                       last_week_submitted = $4
                   WHERE discord_id = $5""",
                daily_streak, weekly_streak, last_submission_date, last_week_submitted, discord_id
            )
        
    # ============ Problem Management Methods ============
    
    async def get_problem(self, problem_slug: str, platform: str = "LeetCode") -> Optional[dict]:
        """
        Get problem information by slug and platform
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic, 
                          date_posted, is_potd, potd_date
                   FROM Problems 
                   WHERE problem_slug = $1 AND platform = $2""",
                problem_slug, platform
            )
            if row:
                return {
                    "problem_slug": row[0],
                    "platform": row[1],
                    "problem_title": row[2],
                    "difficulty": row[3],
                    "academic_year": row[4],
                    "topic": row[5],
                    "date_posted": row[6],
                    "is_potd": row[7],
                    "potd_date": row[8]
                }
        return None
    
    async def create_problem(
        self, 
        problem_slug: str,
        platform: str = "LeetCode",
        problem_title: str = None,
        difficulty: str = None,
        academic_year: str = None,
        topic: str = None, 
        date_posted: str = None,
        is_potd: int = 0,
        potd_date: str = None
    ) -> None:
        """
        Add or Update a problem in the database
        """
        # Backward compatibility: If difficulty is "1", "2", or "3", treat as academic_year
        if difficulty in ["1", "2", "3"] and not academic_year:
            academic_year = difficulty
            difficulty = "Medium"
        
        existing = await self.get_problem(problem_slug, platform)
        
        async with self.pool.acquire() as conn:
            if existing:
                # Update provided fields dynamically
                updates = []
                params = []
                param_idx = 1
                
                if problem_title:
                    updates.append(f"problem_title = ${param_idx}")
                    params.append(problem_title)
                    param_idx += 1
                if difficulty:
                    updates.append(f"difficulty = ${param_idx}")
                    params.append(difficulty)
                    param_idx += 1
                if academic_year:
                    updates.append(f"academic_year = ${param_idx}")
                    params.append(academic_year)
                    param_idx += 1
                if topic:
                    updates.append(f"topic = ${param_idx}")
                    params.append(topic)
                    param_idx += 1
                if date_posted is not None:
                    updates.append(f"date_posted = ${param_idx}")
                    params.append(date_posted)
                    param_idx += 1
                if is_potd is not None:
                    updates.append(f"is_potd = ${param_idx}")
                    params.append(is_potd)
                    param_idx += 1
                if potd_date is not None:
                    updates.append(f"potd_date = ${param_idx}")
                    params.append(potd_date)
                    param_idx += 1
                
                if updates:
                    params.extend([problem_slug, platform])
                    query = f"UPDATE Problems SET {', '.join(updates)} WHERE problem_slug = ${param_idx} AND platform = ${param_idx + 1}"
                    await conn.execute(query, *params)
            else:
                # Insert new problem
                await conn.execute(
                    """INSERT INTO Problems 
                       (problem_slug, platform, problem_title, difficulty, academic_year, topic, date_posted, is_potd, potd_date) 
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                    problem_slug,
                    platform,
                    problem_title or "Unknown Title", 
                    difficulty or "Medium",
                    academic_year or "2",
                    topic or "General", 
                    date_posted,
                    is_potd or 0,
                    potd_date
                )
                
    # ============ Submission Management Methods ============
    
    async def create_submission(
        self,
        discord_id: int,
        problem_slug: str,
        submission_date: str,
        points_awarded: int,
        platform: str = "LeetCode", 
        verification_status: str = "Verified"
    ) -> int:
        """
        Record a new submission
        
        Returns:
            ID of the created submission
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO Submissions 
                   (discord_id, problem_slug, platform, submission_date, points_awarded, verification_status)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING submission_id""",
                discord_id, problem_slug, platform, submission_date, points_awarded, verification_status
            )
            return row[0]
        
    async def get_user_submissions(self, discord_id: int, limit: int = 10) -> list[dict]:
        """
        Get recent submissions for a user
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT s.submission_id, s.discord_id, s.problem_slug, s.platform,
                          s.submission_date, s.points_awarded, p.difficulty
                   FROM Submissions s
                   JOIN Problems p ON s.problem_slug = p.problem_slug AND s.platform = p.platform
                   WHERE s.discord_id = $1
                   ORDER BY s.submission_date DESC
                   LIMIT $2""",
                discord_id, limit
            )
            return [
                {
                    "submission_id": row[0],
                    "discord_id": row[1],
                    "problem_slug": row[2],
                    "platform": row[3],
                    "submission_date": row[4],
                    "points_awarded": row[5],
                    "difficulty": row[6]
                }
                for row in rows
            ]
            
    async def check_duplicate_submission(
        self, 
        discord_id: int, 
        problem_slug: str,
        platform: str = "LeetCode"
    ) -> bool:
        """
        Check if user has already submitted this problem on this platform
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COUNT(*) FROM Submissions 
                   WHERE discord_id = $1 AND problem_slug = $2 AND platform = $3""",
                discord_id, problem_slug, platform
            )
            return row[0] > 0
            
    # ============ Leaderboard Methods ============
    
    async def get_leaderboard(self, limit: int = 10, year: str = None, period: str = None, start_date: str = None, end_date: str = None) -> list[dict]:
        """
        Get top users by points, with optional filters for year and time period
        """
        async with self.pool.acquire() as conn:
            if period and period != "all-time":
                # Period-based leaderboard
                query = """SELECT 
                               u.discord_id, 
                               COALESCE(SUM(s.points_awarded), 0) as total_points,
                               u.daily_streak,
                               u.weekly_streak,
                               u.student_year
                           FROM Users u
                           LEFT JOIN Submissions s ON u.discord_id = s.discord_id"""
                
                conditions = []
                params = []
                param_idx = 1
                
                if start_date and end_date:
                    conditions.append(f"s.submission_date BETWEEN ${param_idx} AND ${param_idx + 1}")
                    params.extend([start_date, end_date])
                    param_idx += 2
                
                if year:
                    conditions.append(f"u.student_year = ${param_idx}")
                    params.append(year)
                    param_idx += 1
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += f" GROUP BY u.discord_id, u.daily_streak, u.weekly_streak, u.student_year ORDER BY total_points DESC LIMIT ${param_idx}"
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
            else:
                # All-time leaderboard
                if year:
                    rows = await conn.fetch(
                        """SELECT discord_id, total_points, daily_streak, weekly_streak, student_year
                           FROM Users
                           WHERE student_year = $1
                           ORDER BY total_points DESC
                           LIMIT $2""",
                        year, limit
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT discord_id, total_points, daily_streak, weekly_streak, student_year
                           FROM Users
                           ORDER BY total_points DESC
                           LIMIT $1""",
                        limit
                    )
            
            return [
                {
                    "discord_id": row[0],
                    "total_points": row[1],
                    "daily_streak": row[2],
                    "weekly_streak": row[3],
                    "student_year": row[4] if len(row) > 4 else None
                }
                for row in rows
            ]

    # ============ POTD Specific Methods ============

    async def set_potd(self, problem_slug: str, platform: str, potd_date: str) -> None:
        """Mark a problem as POTD for a specific date"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE Problems 
                   SET is_potd = 1, potd_date = $1 
                   WHERE problem_slug = $2 AND platform = $3""",
                potd_date, problem_slug, platform
            )

    async def clear_old_potd(self, current_date: str) -> None:
        """Clear POTD status from problems that are not from today"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE Problems 
                   SET is_potd = 0
                   WHERE is_potd = 1 AND (potd_date IS NULL OR potd_date < $1)""",
                current_date
            )
            logger.info(f"Cleared old POTDs: {result}")

    async def unset_potd(self, problem_slug: str, platform: str) -> None:
        """Remove POTD status from a problem (keeps potd_date as historical record)"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE Problems 
                   SET is_potd = 0
                   WHERE problem_slug = $1 AND platform = $2""",
                problem_slug, platform
            )

    async def get_potd_for_date(self, potd_date: str, platform: str = None) -> list[dict]:
        """Get all POTD problems for a specific date"""
        async with self.pool.acquire() as conn:
            if platform:
                rows = await conn.fetch(
                    """SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic
                       FROM Problems 
                       WHERE is_potd = 1 AND potd_date = $1 AND platform = $2""",
                    potd_date, platform
                )
            else:
                rows = await conn.fetch(
                    """SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic
                       FROM Problems 
                       WHERE is_potd = 1 AND potd_date = $1""",
                    potd_date
                )
            
            return [
                {
                    "problem_slug": row[0],
                    "platform": row[1],
                    "problem_title": row[2],
                    "difficulty": row[3],
                    "academic_year": row[4],
                    "topic": row[5]
                }
                for row in rows
            ]

    async def is_problem_potd(self, problem_slug: str, platform: str, date_str: str) -> bool:
        """Check if a problem is POTD for a specific date"""
        async with self.pool.acquire() as conn:
            # Check date_posted (legacy)
            row = await conn.fetchrow(
                "SELECT 1 FROM Problems WHERE problem_slug = $1 AND platform = $2 AND date_posted = $3",
                problem_slug, platform, date_str
            )
            if row:
                return True
            
            # Check is_potd flag
            row = await conn.fetchrow(
                "SELECT 1 FROM Problems WHERE problem_slug = $1 AND platform = $2 AND is_potd = 1 AND potd_date = $3",
                problem_slug, platform, date_str
            )
            return row is not None
    
    async def get_user_potd_count(self, discord_id: int, platform: str, date_str: str) -> int:
        """Count how many POTD problems a user has solved for a specific platform and date."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COUNT(DISTINCT s.problem_slug)
                   FROM Submissions s
                   JOIN Problems p ON s.problem_slug = p.problem_slug AND s.platform = p.platform
                   WHERE s.discord_id = $1 
                     AND s.platform = $2
                     AND p.date_posted = $3""",
                discord_id, platform, date_str
            )
            return row[0] if row else 0

    # ============ Queue Management Methods ============

    async def get_next_queue_batch(self) -> dict:
        """
        Selects the oldest unused problem for Year 1, 2, and 3.
        Returns a dict: {'1': prob_obj, '2': prob_obj, '3': prob_obj}
        """
        batch = {}
        categories = ["1", "2", "3"]
        
        async with self.pool.acquire() as conn:
            for year in categories:
                # Select oldest problem by id (replaces SQLite rowid)
                row = await conn.fetchrow(
                    """SELECT problem_slug, problem_title, difficulty, academic_year, platform 
                       FROM Problems 
                       WHERE academic_year = $1 
                         AND (is_potd = 0 OR is_potd IS NULL)
                         AND potd_date IS NULL
                       ORDER BY id ASC 
                       LIMIT 1""",
                    year
                )
                if row:
                    batch[year] = {
                        "slug": row[0],
                        "title": row[1],
                        "difficulty": row[2],
                        "academic_year": row[3],
                        "platform": row[4],
                        "url": self._generate_url(row[4], row[0])
                    }
        
        return batch

    async def get_queue_status(self) -> dict:
        """Counts how many unused problems remain for each year."""
        status = {}
        async with self.pool.acquire() as conn:
            for year in ["1", "2", "3"]:
                row = await conn.fetchrow(
                    """SELECT COUNT(*) FROM Problems 
                       WHERE academic_year = $1 AND potd_date IS NULL""",
                    year
                )
                status[year] = row[0]
        return status

    async def get_queue_preview(self, limit: int = 5) -> list:
        """Get a list of upcoming problems across all categories."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT problem_title, academic_year, platform 
                   FROM Problems 
                   WHERE potd_date IS NULL 
                   ORDER BY id ASC 
                   LIMIT $1""",
                limit
            )
            return [(row[0], row[1], row[2]) for row in rows]

    def _generate_url(self, platform, slug):
        if platform == "LeetCode": 
            return f"https://leetcode.com/problems/{slug}/"
        if platform == "Codeforces": 
            return f"https://codeforces.com/problemset/problem/{slug}"
        return f"https://www.geeksforgeeks.org/problems/{slug}/"
