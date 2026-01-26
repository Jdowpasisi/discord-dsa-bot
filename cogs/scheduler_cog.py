"""
SchedulerCog: Queue-Based System
--------------------------------
- Reads from a strict ordered queue in problem_bank.json.
- Runs at 12:00 AM IST (UTC+5:30).
- PLATFORM-AWARE: Problems are now stored with platform information
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from database.manager import DatabaseManager
from utils.logic import normalize_problem_name

logger = logging.getLogger(__name__)

# Define IST Timezone (UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class SchedulerCog(commands.Cog):
    
    QUEUE_PATH = Path("data/problem_bank.json")
    CHANNEL_NAME = "potd"
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_manager: DatabaseManager = bot.db
        
        # Start the midnight job
        self.daily_problem_post.start()
        logger.info("SchedulerCog (Queue Mode - Platform Aware) initialized")
    
    def cog_unload(self):
        self.daily_problem_post.cancel()

    # ==================== Queue Management ====================

    def _load_queue(self) -> List[List[Dict]]:
        """Load the list of daily sets."""
        try:
            with open(self.QUEUE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("queue", [])
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            return []

    def _save_queue(self, queue: List[List[Dict]]):
        """Save the modified queue back to JSON."""
        try:
            with open(self.QUEUE_PATH, 'w', encoding='utf-8') as f:
                json.dump({"queue": queue}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def _get_next_batch(self, consume: bool = False) -> Optional[List[Dict]]:
        """
        Get the next set of problems.
        Args:
            consume: If True, removes the set from the JSON file.
        """
        queue = self._load_queue()
        
        if not queue:
            return None
        
        next_set = queue[0]
        
        if consume:
            queue.pop(0)
            self._save_queue(queue)
            logger.info(f"Consumed 1 daily set. Remaining: {len(queue)}")
            
        return next_set

    # ==================== Database & Posting ====================

    async def _process_batch(self, problems: List[Dict], note: str = ""):
        """Insert to DB and Post to Discord"""
        today = datetime.now() # Stores local server time in DB, which is fine
        
        # 1. Insert into Database
        try:
            for p in problems:
                # ✅ FIXED: Added platform parameter (defaults to LeetCode for backward compatibility)
                platform = p.get("platform", "LeetCode")
                await self.db_manager.create_problem(
                    problem_slug=p["slug"],
                    platform=platform,  # ← ADDED PLATFORM
                    problem_title=p["title"],
                    difficulty=p["difficulty"], 
                    topic="Daily Queue",
                    date_posted=today.date().isoformat()
                )
        except Exception as e:
            logger.error(f"DB Insert failed: {e}")
            # We continue even if DB fails, to at least try posting to Discord

        # 2. Create Embed
        embed = discord.Embed(
            title=f"📅 Problem of the Day {note}",
            description="**Topic:** Daily Mix\n**Deadline:** 11:59 PM Today",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        order_map = {"1st Year": 1, "2nd Year": 2, "3rd Year": 3}
        problems.sort(key=lambda x: order_map.get(x["difficulty"], 99))

        for p in problems:
            platform = p.get("platform", "LeetCode")
            embed.add_field(
                name=f"🔹 {p['difficulty']} Problem ({platform})",
                value=f"**{p['title']}**\n[Solve on {platform}]({p['url']})",
                inline=False
            )
            
        embed.set_footer(text=f"Queue Remaining: {len(self._load_queue())}")

        # 3. Post
        channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
        if channel:
            await channel.send(embed=embed)
            logger.info(f"Posted daily batch to #{self.CHANNEL_NAME}")
        else:
            logger.error(f"Channel #{self.CHANNEL_NAME} not found.")

    # ==================== Admin Commands ====================

    @app_commands.command(name="force_potd", description="Admin: Post next POTD but KEEP it in queue (Preview)")
    @app_commands.checks.has_permissions(administrator=True)
    async def force_potd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        batch = self._get_next_batch(consume=False)
        
        if not batch:
            await interaction.followup.send("⚠️ The Queue is empty! Use `python add_problems.py` to add more.")
            return

        await self._process_batch(batch, note="(Preview / Force)")
        await interaction.followup.send("✅ Posted top of queue (Queue NOT consumed).")

    @app_commands.command(name="force_queue", description="Admin: Trigger daily job immediately (Post + Remove from Queue)")
    @app_commands.checks.has_permissions(administrator=True)
    async def force_queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        batch = self._get_next_batch(consume=True)
        
        if not batch:
            await interaction.followup.send("⚠️ The Queue is empty!")
            return

        await self._process_batch(batch)
        await interaction.followup.send("✅ Triggered Daily Job (Queue consumed).")

    # ==================== Scheduled Task ====================

    # CRITICAL CHANGE: Added tzinfo=IST to run at 12:00 AM Indian Standard Time
    @tasks.loop(time=time(hour=0, minute=0, tzinfo=IST))
    async def daily_problem_post(self):
        """Runs automatically at midnight IST."""
        logger.info("Running daily queue task (Scheduled)...")
        
        try:
            batch = self._get_next_batch(consume=True)
            
            if batch:
                await self._process_batch(batch)
            else:
                logger.error("Daily task failed: Queue is empty!")
        except Exception as e:
            logger.error(f"Critical error in daily task: {e}", exc_info=True)

    @daily_problem_post.before_loop
    async def before_daily_post(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
    logger.info("SchedulerCog (Queue - Platform Aware) loaded")