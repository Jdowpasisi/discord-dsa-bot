"""
SchedulerCog: Automated daily problem posting with topic rotation.

This cog handles:
- Daily problem selection and posting at 12:00 AM
- Weekly topic rotation
- Sunday revision days (problems from previous topics)
- State persistence across bot restarts
- Duplicate prevention with 30-day lookback
"""

import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class SchedulerCog(commands.Cog):
    
    """Cog for scheduling daily problem posts with topic rotation."""
    
    PROBLEM_BANK_PATH = Path("data/problem_bank.json")
    STATE_FILE_PATH = Path("data/scheduler_state.json")
    CHANNEL_NAME = "potd"
    LOOKBACK_DAYS = 30  # Don't repeat problems posted in last 30 days
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_manager: DatabaseManager = bot.db
        
        # Load problem bank and state
        self.problem_bank = self._load_problem_bank()
        self.state = self._load_state()
        
        # Start the daily task
        self.daily_problem_post.start()
        logger.info("SchedulerCog initialized - daily task started")
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.daily_problem_post.cancel()
        logger.info("SchedulerCog unloaded - daily task cancelled")
    
    # ==================== File I/O ====================
    
    def _load_problem_bank(self) -> Dict:
        """Load problem bank from JSON file."""
        try:
            with open(self.PROBLEM_BANK_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded problem bank with {len(data['topics'])} topics")
            return data
        except FileNotFoundError:
            logger.error(f"Problem bank not found at {self.PROBLEM_BANK_PATH}")
            return {"topics": []}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in problem bank: {e}")
            return {"topics": []}
    
    def _load_state(self) -> Dict:
        """Load scheduler state from JSON file."""
        try:
            with open(self.STATE_FILE_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.info(f"Loaded state - Topic index: {state.get('current_topic_index', 0)}")
            return state
        except FileNotFoundError:
            logger.warning(f"State file not found, creating new one")
            return self._create_default_state()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in state file: {e}")
            return self._create_default_state()
    
    def _create_default_state(self) -> Dict:
        """Create default state structure."""
        state = {
            "current_topic_index": 0,
            "week_start_date": None,
            "recent_problems": []
        }
        self._save_state(state)
        return state
    
    def _save_state(self, state: Optional[Dict] = None):
        """Save current state to JSON file."""
        if state is None:
            state = self.state
        
        try:
            # Ensure directory exists
            self.STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.STATE_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    # ==================== Topic Management ====================
    
    def _get_current_topic(self) -> Optional[Dict]:
        """Get the current topic based on state."""
        topics = self.problem_bank.get("topics", [])
        if not topics:
            return None
        
        index = self.state.get("current_topic_index", 0)
        # Ensure index is within bounds
        index = index % len(topics)
        return topics[index]
    
    def _rotate_topic(self):
        """Rotate to the next topic."""
        topics = self.problem_bank.get("topics", [])
        if not topics:
            return
        
        current_index = self.state.get("current_topic_index", 0)
        new_index = (current_index + 1) % len(topics)
        
        self.state["current_topic_index"] = new_index
        self.state["week_start_date"] = datetime.now().isoformat()
        self._save_state()
        
        logger.info(f"Rotated topic from index {current_index} to {new_index}")
    
    def _should_rotate_topic(self) -> bool:
        """Check if it's time to rotate to next topic (weekly rotation)."""
        week_start = self.state.get("week_start_date")
        
        # First run or no week start date
        if not week_start:
            return True
        
        try:
            start_date = datetime.fromisoformat(week_start)
            days_elapsed = (datetime.now() - start_date).days
            
            # Rotate every 7 days (1 week)
            return days_elapsed >= 7
        except (ValueError, TypeError):
            logger.warning("Invalid week_start_date, forcing rotation")
            return True
    
    # ==================== Problem Selection ====================
    
    async def _get_recent_problem_slugs(self) -> List[str]:
        """Get problem slugs posted in the last LOOKBACK_DAYS."""
        cutoff_date = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)
        
        try:
            async with self.db_manager.db.execute(
                """
                SELECT problem_slug 
                FROM Problems 
                WHERE date_posted >= ?
                """,
                (cutoff_date.date(),)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch recent problems: {e}")
            return []
    
    def _select_problems_by_difficulty(
        self, 
        topic: Dict, 
        recent_slugs: List[str],
        is_revision: bool = False
    ) -> Optional[Tuple[Dict, Dict, Dict]]:
        """
        Select 1 Easy, 1 Medium, 1 Hard problem from topic.
        
        Args:
            topic: Topic dictionary with problems
            recent_slugs: List of recently posted problem slugs to avoid
            is_revision: If True, prefer problems not from current topic
            
        Returns:
            Tuple of (easy_problem, medium_problem, hard_problem) or None
        """
        problems = topic.get("problems", [])
        
        # Filter out recent problems
        available = [p for p in problems if p["slug"] not in recent_slugs]
        
        # Group by difficulty
        easy = [p for p in available if p["difficulty"] == "Easy"]
        medium = [p for p in available if p["difficulty"] == "Medium"]
        hard = [p for p in available if p["difficulty"] == "Hard"]
        
        # Check if we have enough problems
        if not easy or not medium or not hard:
            logger.warning(f"Insufficient problems in topic '{topic['name']}': "
                          f"Easy={len(easy)}, Medium={len(medium)}, Hard={len(hard)}")
            return None
        
        # Randomly select one from each difficulty
        selected_easy = random.choice(easy)
        selected_medium = random.choice(medium)
        selected_hard = random.choice(hard)
        
        return (selected_easy, selected_medium, selected_hard)
    
    def _select_revision_problems(
        self, 
        recent_slugs: List[str]
    ) -> Optional[Tuple[Dict, Dict, Dict]]:
        """
        Select problems from previous topics for Sunday revision.
        
        Returns:
            Tuple of (easy_problem, medium_problem, hard_problem) or None
        """
        topics = self.problem_bank.get("topics", [])
        if len(topics) < 2:
            # Not enough topics for revision, use current topic
            return None
        
        current_index = self.state.get("current_topic_index", 0)
        
        # Get all previous topics (exclude current)
        previous_topics = [
            topic for i, topic in enumerate(topics) 
            if i != current_index
        ]
        
        if not previous_topics:
            return None
        
        # Try each previous topic until we find sufficient problems
        random.shuffle(previous_topics)
        
        for topic in previous_topics:
            result = self._select_problems_by_difficulty(topic, recent_slugs, is_revision=True)
            if result:
                logger.info(f"Selected revision problems from topic '{topic['name']}'")
                return result
        
        logger.warning("Failed to select revision problems from any previous topic")
        return None
    
    # ==================== Database Operations ====================
    
    async def _insert_problems_to_db(self, problems: List[Dict], today: datetime):
        """Insert selected problems into the Problems table."""
        try:
            for problem in problems:
                await self.db_manager.create_problem(
                    problem_slug=problem["slug"],
                    problem_title=problem["title"],
                    difficulty=problem["difficulty"],
                    topic=problem.get("topic", "Unknown"),
                    date_posted=today.date()
                )
            logger.info(f"Inserted {len(problems)} problems to database")
        except Exception as e:
            logger.error(f"Failed to insert problems to database: {e}")
            raise
    
    # ==================== Discord Posting ====================
    
    def _create_problem_embed(
        self, 
        problems: List[Dict], 
        topic_name: str,
        is_revision: bool = False
    ) -> discord.Embed:
        """Create rich embed for daily problems."""
        title = f"📅 Daily Challenge - {topic_name}" if not is_revision else "🔄 Sunday Revision Challenge"
        
        embed = discord.Embed(
            title=title,
            description=f"**Topic:** {topic_name}\n**Deadline:** 11:59 PM Today",
            color=discord.Color.blue() if not is_revision else discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        # Add each problem as a field
        difficulty_emojis = {
            "Easy": "🟢",
            "Medium": "🟡",
            "Hard": "🔴"
        }
        
        for i, problem in enumerate(problems, 1):
            emoji = difficulty_emojis.get(problem["difficulty"], "⚪")
            field_name = f"{emoji} Problem {i}: {problem['title']}"
            field_value = f"**Difficulty:** {problem['difficulty']}\n[Solve on LeetCode]({problem['url']})"
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        # Footer with instructions
        embed.set_footer(text="Use /submit <difficulty> <problem-name> to record your solution!")
        
        return embed
    
    async def _post_to_channel(self, embed: discord.Embed) -> bool:
        """Post embed to the potd channel."""
        try:
            # Find the channel
            channel = discord.utils.get(
                self.bot.get_all_channels(),
                name=self.CHANNEL_NAME
            )
            
            if not channel:
                logger.error(f"Channel '{self.CHANNEL_NAME}' not found")
                return False
            
            # Post the embed
            await channel.send(embed=embed)
            logger.info(f"Posted daily problems to #{self.CHANNEL_NAME}")
            return True
            
        except discord.Forbidden:
            logger.error(f"No permission to post in #{self.CHANNEL_NAME}")
            return False
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
            return False
    
    # ==================== Manual Testing Command ====================
    
    @commands.command(name="force_potd", hidden=True)
    @commands.is_owner()
    async def force_potd(self, ctx: commands.Context):
        """
        Manually trigger the daily POTD immediately (Owner only).
        
        This command is for testing purposes and should only be used by the bot owner.
        It calls the daily_job logic without waiting for scheduled time.
        """
        await ctx.send("✅ Manually triggered Daily POTD.")
        
        try:
            # Call the main daily problem post logic
            await self.daily_problem_post()
            logger.info(f"Force POTD triggered by {ctx.author} ({ctx.author.id})")
        except Exception as e:
            await ctx.send(f"❌ Error during POTD execution: {e}")
            logger.error(f"Force POTD failed: {e}", exc_info=True)
    
    # ==================== Main Task ====================
    
    @tasks.loop(time=time(hour=0, minute=0))  # Run at 12:00 AM
    async def daily_problem_post(self):
        """Main task: Select and post daily problems."""
        try:
            logger.info("Starting daily problem post task")
            
            today = datetime.now()
            is_sunday = today.weekday() == 6  # Sunday = 6
            
            # Check if we should rotate topic (weekly rotation)
            if self._should_rotate_topic() and not is_sunday:
                self._rotate_topic()
            
            # Get recent problems to avoid duplicates
            recent_slugs = await self._get_recent_problem_slugs()
            logger.info(f"Found {len(recent_slugs)} recent problems to avoid")
            
            # Select problems based on day
            if is_sunday:
                # Revision day: problems from previous topics
                selected = self._select_revision_problems(recent_slugs)
                topic_name = "Mixed Review"
            else:
                # Regular day: problems from current topic
                current_topic = self._get_current_topic()
                
                if not current_topic:
                    logger.error("No topics available in problem bank")
                    return
                
                selected = self._select_problems_by_difficulty(current_topic, recent_slugs)
                topic_name = current_topic["name"]
            
            if not selected:
                logger.error("Failed to select problems")
                return
            
            easy_prob, medium_prob, hard_prob = selected
            problems = [easy_prob, medium_prob, hard_prob]
            
            # Add topic to each problem for DB storage
            for prob in problems:
                prob["topic"] = topic_name
            
            # Insert to database
            await self._insert_problems_to_db(problems, today)
            
            # Update state with recent problems
            self.state["recent_problems"] = recent_slugs[:50]  # Keep last 50
            self._save_state()
            
            # Create and post embed
            embed = self._create_problem_embed(problems, topic_name, is_revision=is_sunday)
            success = await self._post_to_channel(embed)
            
            if success:
                logger.info(f"✅ Daily post completed: {topic_name} "
                           f"({'Revision' if is_sunday else 'Regular'})")
            else:
                logger.error("Failed to post to Discord channel")
                
        except Exception as e:
            logger.error(f"Error in daily_problem_post task: {e}", exc_info=True)
    
    @daily_problem_post.before_loop
    async def before_daily_post(self):
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()
        logger.info("Bot ready - scheduler task will begin")
    
    # ==================== Manual Commands (for testing) ====================
    
    @commands.command(name="post_now")
    @commands.has_permissions(administrator=True)
    async def manual_post(self, ctx: commands.Context):
        """Manually trigger the daily post (Admin only)."""
        await ctx.send("⏳ Manually triggering daily post...")
        
        try:
            await self.daily_problem_post()
            await ctx.send("✅ Daily post completed successfully!")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            logger.error(f"Manual post failed: {e}", exc_info=True)
    
    @commands.command(name="rotate_topic")
    @commands.has_permissions(administrator=True)
    async def manual_rotate(self, ctx: commands.Context):
        """Manually rotate to next topic (Admin only)."""
        old_topic = self._get_current_topic()
        old_name = old_topic["name"] if old_topic else "Unknown"
        
        self._rotate_topic()
        
        new_topic = self._get_current_topic()
        new_name = new_topic["name"] if new_topic else "Unknown"
        
        await ctx.send(f"✅ Rotated topic: **{old_name}** → **{new_name}**")
    
    @commands.command(name="current_topic")
    async def show_current_topic(self, ctx: commands.Context):
        """Show the current topic."""
        topic = self._get_current_topic()
        
        if not topic:
            await ctx.send("❌ No topics available")
            return
        
        week_start = self.state.get("week_start_date", "Unknown")
        embed = discord.Embed(
            title="📚 Current Topic",
            description=f"**Topic:** {topic['name']}\n"
                       f"**Problems:** {len(topic.get('problems', []))}\n"
                       f"**Week Started:** {week_start}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="scheduler_status")
    @commands.has_permissions(administrator=True)
    async def scheduler_status(self, ctx: commands.Context):
        """Show scheduler status and configuration (Admin only)."""
        topic = self._get_current_topic()
        topic_name = topic["name"] if topic else "None"
        
        next_run = self.daily_problem_post.next_iteration
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "Not scheduled"
        
        embed = discord.Embed(
            title="⚙️ Scheduler Status",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Task Status",
            value=f"{'✅ Running' if self.daily_problem_post.is_running() else '❌ Stopped'}",
            inline=True
        )
        
        embed.add_field(
            name="Next Run",
            value=next_run_str,
            inline=True
        )
        
        embed.add_field(
            name="Current Topic",
            value=f"{topic_name} (Index: {self.state.get('current_topic_index', 0)})",
            inline=False
        )
        
        embed.add_field(
            name="Week Started",
            value=self.state.get("week_start_date", "Not set"),
            inline=True
        )
        
        embed.add_field(
            name="Recent Problems Tracked",
            value=str(len(self.state.get("recent_problems", []))),
            inline=True
        )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the SchedulerCog."""
    await bot.add_cog(SchedulerCog(bot))
    logger.info("SchedulerCog loaded successfully")
