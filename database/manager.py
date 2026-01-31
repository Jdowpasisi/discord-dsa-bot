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
        if exclude_discord_id:
            async with self.db.execute(
                f"SELECT discord_id FROM Users WHERE {handle_type} = ? AND discord_id != ?",
                (handle_value, exclude_discord_id)
            ) as cursor:
                return await cursor.fetchone() is not None
        else:
            async with self.db.execute(
                f"SELECT discord_id FROM Users WHERE {handle_type} = ?",
                (handle_value,)
            ) as cursor:
                return await cursor.fetchone() is not None
    
    async def delete_user(self, discord_id: int) -> None:
        """
        Delete a user and all their submissions from the database.
        
        Args:
            discord_id: Discord user ID to delete
        """
        await self.db.execute("DELETE FROM Submissions WHERE discord_id = ?", (discord_id,))
        await self.db.execute("DELETE FROM Users WHERE discord_id = ?", (discord_id,))
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
        """
        # Ensure we select is_potd and potd_date
        async with self.db.execute(
            """
            SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic, 
                   date_posted, is_potd, potd_date
            FROM Problems 
            WHERE problem_slug = ? AND platform = ?
            """,
            (problem_slug, platform)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "problem_slug": row[0],
                    "platform": row[1],
                    "problem_title": row[2],
                    "difficulty": row[3],
                    "academic_year": row[4],
                    "topic": row[5],
                    "date_posted": row[6], # Deprecated but kept
                    "is_potd": row[7],     # CRITICAL: This was missing
                    "potd_date": row[8]    # CRITICAL: This was missing
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
        date_posted: str = None
    ) -> None:
        """
        Add or Update a problem in the database
        
        Args:
            problem_slug: Problem slug
            platform: Platform name (LeetCode, Codeforces, GeeksforGeeks)
            problem_title: Problem title
            difficulty: Problem difficulty (Easy, Medium, Hard)
            academic_year: Academic year level ("1", "2", "3")
            topic: Problem topic/category
            date_posted: Date when problem was posted as POTD (YYYY-MM-DD)
        """
        # Backward compatibility: If difficulty is "1", "2", or "3", treat as academic_year
        if difficulty in ["1", "2", "3"] and not academic_year:
            academic_year = difficulty
            difficulty = "Medium"  # Default difficulty
        
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
            if academic_year:
                updates.append("academic_year = ?")
                params.append(academic_year)
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
                (problem_slug, platform, problem_title, difficulty, academic_year, topic, date_posted) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    problem_slug,
                    platform,
                    problem_title or "Unknown Title", 
                    difficulty or "Medium",
                    academic_year or "2",  # Default to year 2 if not specified
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
    
    async def get_leaderboard(self, limit: int = 10, year: str = None, period: str = None, start_date: str = None, end_date: str = None) -> list[dict]:
        """
        Get top users by points, with optional filters for year and time period
        
        Args:
            limit: Number of top users to return
            year: Optional student year filter ("1", "2", "3", "4")
            period: Optional period filter ("weekly", "monthly", "all-time")
            start_date: Start date for period filter (ISO format)
            end_date: End date for period filter (ISO format)
            
        Returns:
            List of user dictionaries sorted by points
        """
        if period and period != "all-time":
            # Period-based leaderboard: JOIN with Submissions and sum points_awarded
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
            
            if start_date and end_date:
                conditions.append("s.submission_date BETWEEN ? AND ?")
                params.extend([start_date, end_date])
            
            if year:
                conditions.append("u.student_year = ?")
                params.append(year)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " GROUP BY u.discord_id ORDER BY total_points DESC LIMIT ?"
            params.append(limit)
        else:
            # All-time leaderboard: use total_points from Users table
            if year:
                query = """SELECT discord_id, total_points, daily_streak, weekly_streak, student_year
                           FROM Users
                           WHERE student_year = ?
                           ORDER BY total_points DESC
                           LIMIT ?"""
                params = (year, limit)
            else:
                query = """SELECT discord_id, total_points, daily_streak, weekly_streak, student_year
                           FROM Users
                           ORDER BY total_points DESC
                           LIMIT ?"""
                params = (limit,)
        
        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
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
        """
        Mark a problem as POTD for a specific date
        
        Args:
            problem_slug: Problem slug
            platform: Platform name
            potd_date: Date string in YYYY-MM-DD format
        """
        await self.db.execute(
            """UPDATE Problems 
            SET is_potd = 1, potd_date = ? 
            WHERE problem_slug = ? AND platform = ?""",
            (potd_date, problem_slug, platform)
        )
        await self.db.commit()

    async def unset_potd(self, problem_slug: str, platform: str) -> None:
        """
        Remove POTD status from a problem
        
        Args:
            problem_slug: Problem slug
            platform: Platform name
        """
        await self.db.execute(
            """UPDATE Problems 
            SET is_potd = 0, potd_date = NULL 
            WHERE problem_slug = ? AND platform = ?""",
            (problem_slug, platform)
        )
        await self.db.commit()

    async def get_potd_for_date(self, potd_date: str, platform: str = None) -> list[dict]:
        """
        Get all POTD problems for a specific date
        
        Args:
            potd_date: Date string in YYYY-MM-DD format
            platform: Optional platform filter
            
        Returns:
            List of problem dictionaries
        """
        if platform:
            query = """SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic
                    FROM Problems 
                    WHERE is_potd = 1 AND potd_date = ? AND platform = ?"""
            params = (potd_date, platform)
        else:
            query = """SELECT problem_slug, platform, problem_title, difficulty, academic_year, topic
                    FROM Problems 
                    WHERE is_potd = 1 AND potd_date = ?"""
            params = (potd_date,)
        
        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
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
        """
        Check if a problem is POTD for a specific date (UPDATED)
        
        Args:
            problem_slug: Problem slug
            platform: Platform name
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if problem is POTD, False otherwise
        """
        async with self.db.execute(
            """SELECT 1 FROM Problems 
            WHERE problem_slug = ? AND platform = ? AND is_potd = 1 AND potd_date = ?""",
            (problem_slug, platform, date_str)
        ) as cursor:
            return await cursor.fetchone() is not None

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
        Add or Update a problem in the database (UPDATED)
        
        Args:
            problem_slug: Problem slug
            platform: Platform name
            problem_title: Problem title
            difficulty: Problem difficulty (Easy, Medium, Hard)
            academic_year: Academic year level ("1", "2", "3")
            topic: Problem topic/category
            date_posted: DEPRECATED - kept for backwards compatibility
            is_potd: 1 if POTD, 0 otherwise
            potd_date: Date when set as POTD (YYYY-MM-DD)
        """
        # Backward compatibility: If difficulty is "1", "2", or "3", treat as academic_year
        if difficulty in ["1", "2", "3"] and not academic_year:
            academic_year = difficulty
            difficulty = "Medium"  # Default difficulty
        
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
            if academic_year:
                updates.append("academic_year = ?")
                params.append(academic_year)
            if topic:
                updates.append("topic = ?")
                params.append(topic)
            if date_posted is not None:
                updates.append("date_posted = ?")
                params.append(date_posted)
            if is_potd is not None:
                updates.append("is_potd = ?")
                params.append(is_potd)
            if potd_date is not None:
                updates.append("potd_date = ?")
                params.append(potd_date)
            
            if updates:
                params.extend([problem_slug, platform])
                query = f"UPDATE Problems SET {', '.join(updates)} WHERE problem_slug = ? AND platform = ?"
                await self.db.execute(query, tuple(params))
                await self.db.commit()
        else:
            # Insert new problem
            await self.db.execute(
                """INSERT INTO Problems 
                (problem_slug, platform, problem_title, difficulty, academic_year, topic, date_posted, is_potd, potd_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    problem_slug,
                    platform,
                    problem_title or "Unknown Title", 
                    difficulty or "Medium",
                    academic_year or "2",  # Default to year 2
                    topic or "General", 
                    date_posted,
                    is_potd or 0,
                    potd_date
                )
            )
            await self.db.commit()

    async def is_problem_potd(self, problem_slug: str, platform: str, date_str: str) -> bool:   
        """Check if a problem is assigned as POTD"""
        async with self.db.execute(
            "SELECT 1 FROM Problems WHERE problem_slug = ? AND platform = ? AND date_posted = ?",
            (problem_slug, platform, date_str)
        ) as cursor:
            # Fallback logic: check is_potd flag if date logic fails or vice versa
            if await cursor.fetchone():
                return True
                
        # Also check strict flag + date match
        async with self.db.execute(
            "SELECT 1 FROM Problems WHERE problem_slug = ? AND platform = ? AND is_potd = 1 AND potd_date = ?",
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
        # ============ Queue Management Methods (NEW) ============

    async def get_next_queue_batch(self) -> dict:
        """
        Selects the oldest unused problem for Year 1, 2, and 3.
        Returns a dict: {'1': prob_obj, '2': prob_obj, '3': prob_obj}
        """
        batch = {}
        # Categories mapping
        categories = ["1", "2", "3"]
        
        for year in categories:
            # Select oldest problem (by implicit rowid) that hasn't been POTD yet
            async with self.db.execute(
                """
                SELECT problem_slug, problem_title, difficulty, academic_year, platform 
                FROM Problems 
                WHERE academic_year = ? 
                  AND (is_potd = 0 OR is_potd IS NULL)
                  AND potd_date IS NULL
                ORDER BY rowid ASC 
                LIMIT 1
                """,
                (year,)
            ) as cursor:
                row = await cursor.fetchone()
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
        for year in ["1", "2", "3"]:
            async with self.db.execute(
                """SELECT COUNT(*) FROM Problems 
                   WHERE academic_year = ? AND potd_date IS NULL""",
                (year,)
            ) as cursor:
                status[year] = (await cursor.fetchone())[0]
        return status

    async def get_queue_preview(self, limit: int = 5) -> list:
        """Get a list of upcoming problems across all categories."""
        async with self.db.execute(
            """
            SELECT problem_title, academic_year, platform 
            FROM Problems 
            WHERE potd_date IS NULL 
            ORDER BY rowid ASC 
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

    def _generate_url(self, platform, slug):
        if platform == "LeetCode": return f"https://leetcode.com/problems/{slug}/"
        if platform == "Codeforces": return f"https://codeforces.com/problemset/problem/{slug}"
        return f"https://www.geeksforgeeks.org/problems/{slug}/"