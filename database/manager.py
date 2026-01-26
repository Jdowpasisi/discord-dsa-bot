"""
Database Manager for LeetCode Discord Bot
Handles database connections, initialization, and common queries
"""

import aiosqlite
import os
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """Manages SQLite database operations for the Discord bot"""
    
    def __init__(self, db_path: str = "data/leetcode_bot.db"):
        """
        Initialize the DatabaseManager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None
        
    async def connect(self) -> None:
        """Establish database connection"""
        # Ensure the data directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = await aiosqlite.connect(self.db_path)
        # Enable foreign key support
        await self.db.execute("PRAGMA foreign_keys = ON")
        await self.db.commit()
        print(f"✓ Database connected: {self.db_path}")
        
    async def close(self) -> None:
        """Close database connection"""
        if self.db:
            await self.db.close()
            print("✓ Database connection closed")
            
    async def initialize_tables(self) -> None:
        """Create database tables from schema.sql if they don't exist"""
        if not self.db:
            raise RuntimeError("Database not connected. Call connect() first.")
            
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
        # Read and execute the schema file
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            
        await self.db.executescript(schema_sql)
        await self.db.commit()
        print("✓ Database tables initialized")
        
    # ============ User Management Methods ============
    
    async def get_user(self, discord_id: int) -> Optional[dict]:
        """
        Get user information by Discord ID
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            Dictionary with user data or None if not found
        """
        async with self.db.execute(
            "SELECT * FROM Users WHERE discord_id = ?",
            (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
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
        await self.db.execute(
            "INSERT OR IGNORE INTO Users (discord_id) VALUES (?)",
            (discord_id,)
        )
        await self.db.commit()
        
    async def update_user_profile(
        self, 
        discord_id: int, 
        student_year: str = None, 
        leetcode_username: str = None, 
        codeforces_handle: str = None, 
        gfg_handle: str = None
    ) -> None:
        """
        Update user profile information (year level and/or LeetCode username)
        
        Args:
            discord_id: Discord user ID
            student_year: Student year level (1, 2, 3, 4, or General)
            leetcode_username: LeetCode username
            codeforces_handle: Codeforces handle
            gfg_handle: GeeksforGeeks handle
        """
        updates = []
        params = []
        
        if student_year is not None:
            updates.append("student_year = ?")
            params.append(student_year)
            
        if leetcode_username is not None:
            updates.append("leetcode_username = ?")
            params.append(leetcode_username)
        
        if codeforces_handle is not None:
            updates.append("codeforces_handle = ?")
            params.append(codeforces_handle)
            
        if gfg_handle is not None:
            updates.append("gfg_handle = ?")
            params.append(gfg_handle)
                
        if updates:
            params.append(discord_id)
            query = f"UPDATE Users SET {', '.join(updates)} WHERE discord_id = ?"
            await self.db.execute(query, tuple(params))
            await self.db.commit()
        
    async def update_user_points(self, discord_id: int, points_to_add: int) -> None:
        """
        Update user's total points
        
        Args:
            discord_id: Discord user ID
            points_to_add: Points to add to user's total
        """
        await self.db.execute(
            "UPDATE Users SET total_points = total_points + ? WHERE discord_id = ?",
            (points_to_add, discord_id)
        )
        await self.db.commit()
        
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
        
        Args:
            discord_id: Discord user ID
            daily_streak: New daily streak value
            weekly_streak: New weekly streak value
            last_submission_date: Last submission timestamp
            last_week_submitted: Last week submitted (YYYY-WW format)
        """
        await self.db.execute(
            """UPDATE Users 
               SET daily_streak = ?, 
                   weekly_streak = ?, 
                   last_submission_date = ?,
                   last_week_submitted = ?
               WHERE discord_id = ?""",
            (daily_streak, weekly_streak, last_submission_date, last_week_submitted, discord_id)
        )
        await self.db.commit()
        
    # ============ Problem Management Methods ============
    
    async def get_problem(self, problem_slug: str, platform: str = "LeetCode") -> Optional[dict]:
        """
        Get problem information by slug and platform
        
        Args:
            problem_slug: Problem slug (e.g., "two-sum")
            platform: Platform name (LeetCode, Codeforces, GeeksforGeeks)
            
        Returns:
            Dictionary with problem data or None if not found
        """
        async with self.db.execute(
            "SELECT * FROM Problems WHERE problem_slug = ? AND platform = ?",
            (problem_slug, platform)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "problem_slug": row[0],
                    "platform": row[1],
                    "problem_title": row[2],
                    "difficulty": row[3],
                    "topic": row[4],
                    "date_posted": row[5]
                }
        return None

    async def create_problem(
        self, 
        problem_slug: str,
        platform: str = "LeetCode",
        problem_title: str = None,
        difficulty: str = None, 
        topic: str = None, 
        date_posted: str = None
    ) -> None:
        """
        Add or Update a problem in the database
        
        Args:
            problem_slug: Problem slug
            platform: Platform name (LeetCode, Codeforces, GeeksforGeeks)
            problem_title: Problem title
            difficulty: Problem difficulty
            topic: Problem topic/category
            date_posted: Date when problem was posted as POTD (YYYY-MM-DD)
        """
        # Check if problem already exists
        existing = await self.get_problem(problem_slug, platform)
        
        if existing:
            # Update provided fields
            updates = []
            params = []
            
            if problem_title:
                updates.append("problem_title = ?")
                params.append(problem_title)
            if difficulty:
                updates.append("difficulty = ?")
                params.append(difficulty)
            if topic:
                updates.append("topic = ?")
                params.append(topic)
            if date_posted is not None:  # Changed to explicit None check
                updates.append("date_posted = ?")
                params.append(date_posted)
            
            if updates:
                params.extend([problem_slug, platform])
                query = f"UPDATE Problems SET {', '.join(updates)} WHERE problem_slug = ? AND platform = ?"
                await self.db.execute(query, tuple(params))
                await self.db.commit()
        else:
            # Insert new problem - use NULL explicitly for date_posted if None
            await self.db.execute(
                """INSERT INTO Problems 
                (problem_slug, platform, problem_title, difficulty, topic, date_posted) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    problem_slug,
                    platform,
                    problem_title or "Unknown Title", 
                    difficulty or "Medium", 
                    topic or "General", 
                    date_posted  # This will be None for non-POTD, which SQLite accepts as NULL
                )
            )
            await self.db.commit()   
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
        
        Args:
            discord_id: Discord user ID
            problem_slug: Problem slug
            submission_date: Timestamp of submission
            points_awarded: Points awarded for this submission
            platform: Platform name (LeetCode, Codeforces, GeeksforGeeks)
            verification_status: Status of verification
            
        Returns:
            ID of the created submission
        """
        cursor = await self.db.execute(
            """INSERT INTO Submissions 
               (discord_id, problem_slug, platform, submission_date, points_awarded, verification_status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (discord_id, problem_slug, platform, submission_date, points_awarded, verification_status)
        )
        await self.db.commit()
        return cursor.lastrowid
        
    async def get_user_submissions(self, discord_id: int, limit: int = 10) -> list[dict]:
        """
        Get recent submissions for a user
        
        Args:
            discord_id: Discord user ID
            limit: Maximum number of submissions to return
            
        Returns:
            List of submission dictionaries
        """
        async with self.db.execute(
            """SELECT s.submission_id, s.discord_id, s.problem_slug, s.platform,
                      s.submission_date, s.points_awarded, p.difficulty
               FROM Submissions s
               JOIN Problems p ON s.problem_slug = p.problem_slug AND s.platform = p.platform
               WHERE s.discord_id = ?
               ORDER BY s.submission_date DESC
               LIMIT ?""",
            (discord_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
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
        
        Args:
            discord_id: Discord user ID
            problem_slug: Problem slug
            platform: Platform name
            
        Returns:
            True if submission exists, False otherwise
        """
        async with self.db.execute(
            """SELECT COUNT(*) FROM Submissions 
               WHERE discord_id = ? AND problem_slug = ? AND platform = ?""",
            (discord_id, problem_slug, platform)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] > 0
            
    # ============ Leaderboard Methods ============
    
    async def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """
        Get top users by total points
        
        Args:
            limit: Number of top users to return
            
        Returns:
            List of user dictionaries sorted by points
        """
        async with self.db.execute(
            """SELECT discord_id, total_points, daily_streak, weekly_streak
               FROM Users
               ORDER BY total_points DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "discord_id": row[0],
                    "total_points": row[1],
                    "daily_streak": row[2],
                    "weekly_streak": row[3]
                }
                for row in rows
            ]

    # ============ POTD Specific Methods ============
    
    async def is_problem_potd(self, problem_slug: str, platform: str, date_str: str) -> bool:
        """
        Check if a problem is assigned as POTD for a specific platform and date.
        
        Args:
            problem_slug: Problem slug
            platform: Platform name (LeetCode, Codeforces, GeeksforGeeks)
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if problem is POTD for this platform on this date, False otherwise
        """
        async with self.db.execute(
            "SELECT 1 FROM Problems WHERE problem_slug = ? AND platform = ? AND date_posted = ?",
            (problem_slug, platform, date_str)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def get_user_potd_count(self, discord_id: int, platform: str, date_str: str) -> int:
        """
        Count how many POTD problems a user has solved for a specific platform and date.
        
        Args:
            discord_id: Discord user ID
            platform: Platform name
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Count of POTD problems solved
        """
        query = """
        SELECT COUNT(DISTINCT s.problem_slug)
        FROM Submissions s
        JOIN Problems p ON s.problem_slug = p.problem_slug AND s.platform = p.platform
        WHERE s.discord_id = ? 
          AND s.platform = ?
          AND p.date_posted = ?
        """
        async with self.db.execute(query, (discord_id, platform, date_str)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0