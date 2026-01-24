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
                    "last_week_submitted": row[5]
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
    
    async def get_problem(self, problem_slug: str) -> Optional[dict]:
        """
        Get problem information by slug
        
        Args:
            problem_slug: LeetCode problem slug (e.g., "two-sum")
            
        Returns:
            Dictionary with problem data or None if not found
        """
        async with self.db.execute(
            "SELECT * FROM Problems WHERE problem_slug = ?",
            (problem_slug,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "problem_slug": row[0],
                    "difficulty": row[1],
                    "topic": row[2],
                    "date_posted": row[3]
                }
        return None
        
    async def create_problem(
        self, 
        problem_slug: str, 
        problem_title: str = None,
        difficulty: str = None, 
        topic: str = None, 
        date_posted: str = None
    ) -> None:
        """
        Add a new problem to the database
        
        Args:
            problem_slug: LeetCode problem slug
            problem_title: Human-readable problem title (optional)
            difficulty: Problem difficulty (Easy, Medium, or Hard)
            topic: Problem topic/category
            date_posted: Date when problem was posted
        """
        # Check if problem already exists
        existing = await self.get_problem(problem_slug)
        
        if existing:
            # Update only the fields that are provided
            updates = []
            params = []
            
            if difficulty:
                updates.append("difficulty = ?")
                params.append(difficulty)
            if topic:
                updates.append("topic = ?")
                params.append(topic)
            if date_posted:
                updates.append("date_posted = ?")
                params.append(date_posted)
            
            if updates:
                params.append(problem_slug)
                query = f"UPDATE Problems SET {', '.join(updates)} WHERE problem_slug = ?"
                await self.db.execute(query, tuple(params))
                await self.db.commit()
        else:
            # Insert new problem
            await self.db.execute(
                """INSERT INTO Problems 
                   (problem_slug, difficulty, topic, date_posted) 
                   VALUES (?, ?, ?, ?)""",
                (problem_slug, difficulty or "Medium", topic or "General", date_posted)
            )
            await self.db.commit()
        
    # ============ Submission Management Methods ============
    
    async def create_submission(
        self,
        discord_id: int,
        problem_slug: str,
        submission_date: str,
        points_awarded: int
    ) -> int:
        """
        Record a new submission
        
        Args:
            discord_id: Discord user ID
            problem_slug: LeetCode problem slug
            submission_date: Timestamp of submission
            points_awarded: Points awarded for this submission
            
        Returns:
            ID of the created submission
        """
        cursor = await self.db.execute(
            """INSERT INTO Submissions 
               (discord_id, problem_slug, submission_date, points_awarded)
               VALUES (?, ?, ?, ?)""",
            (discord_id, problem_slug, submission_date, points_awarded)
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
            """SELECT s.submission_id, s.discord_id, s.problem_slug, 
                      s.submission_date, s.points_awarded, p.difficulty
               FROM Submissions s
               JOIN Problems p ON s.problem_slug = p.problem_slug
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
                    "submission_date": row[3],
                    "points_awarded": row[4],
                    "difficulty": row[5]
                }
                for row in rows
            ]
            
    async def check_duplicate_submission(
        self, 
        discord_id: int, 
        problem_slug: str
    ) -> bool:
        """
        Check if user has already submitted this problem
        
        Args:
            discord_id: Discord user ID
            problem_slug: LeetCode problem slug
            
        Returns:
            True if submission exists, False otherwise
        """
        async with self.db.execute(
            """SELECT COUNT(*) FROM Submissions 
               WHERE discord_id = ? AND problem_slug = ?""",
            (discord_id, problem_slug)
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
