"""
SchedulerCog: Database-Driven Queue
-----------------------------------
- Runs at 12:00 AM IST.
- Pulls the oldest unused problems (Year 1, 2, 3) from the Database.
- Sets them as POTD.
- Includes Codeforces URL Fixer.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta, timezone
import logging

from database.manager import DatabaseManager
from utils.logic import generate_problem_url

logger = logging.getLogger(__name__)

# Define IST Timezone (UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class SchedulerCog(commands.Cog):
    
    CHANNEL_NAME = "potd"
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_manager: DatabaseManager = bot.db
        
        # Start the midnight job
        self.daily_problem_post.start()
        logger.info("SchedulerCog (DB Queue Mode) initialized")
    
    def cog_unload(self):
        self.daily_problem_post.cancel()

    # ==================== Core Logic ======================================

    async def _post_daily_batch(self, batch_data: dict, note: str = ""):
        """
        1. Mark problems as POTD in DB.
        2. Post Embed to Discord.
        """
        today_str = datetime.now().date().isoformat()
        
        # Check if we have a full set (1, 2, 3)
        if len(batch_data) < 3:
            logger.warning("Batch incomplete. Missing some years.")

        # 1. Update DB (Set as POTD)
        if not note.startswith("(Preview"): # Only update DB if not a preview
            for year, prob in batch_data.items():
                await self.db_manager.set_potd(prob['slug'], prob['platform'], today_str)
            logger.info(f"Set POTD for {today_str}")

        # 2. Create Embed
        embed = discord.Embed(
            title=f"📅 Problem of the Day {note}",
            description=f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n**Deadline:** 11:59 PM Today",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Sort 1 -> 2 -> 3
        sorted_years = sorted(batch_data.keys())
        
        for year in sorted_years:
            p = batch_data[year]
            
            # Use centralized URL generation from utils.logic
            safe_url = generate_problem_url(p['platform'], p['slug'])
            
            # Display both difficulty and year
            difficulty = p.get('difficulty', 'Medium')
            embed.add_field(
                name=f"🔹 Year {year} ({difficulty}) - {p['platform']}",
                value=f"**{p['title']}**\n[Solve Here]({safe_url})",
                inline=False
            )
        
        # Add Queue Stats to Footer
        q_status = await self.db_manager.get_queue_status()
        footer_text = f"Queue: Y1:{q_status.get('1',0)} | Y2:{q_status.get('2',0)} | Y3:{q_status.get('3',0)}"
        embed.set_footer(text=footer_text)

        # 3. Post
        channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
        if channel:
            await channel.send(embed=embed)
        else:
            logger.error(f"Channel #{self.CHANNEL_NAME} not found.")

    # ==================== Admin Commands ====================

    # @app_commands.command(name="force_potd", description="Admin: Trigger daily job immediately (Consumes Queue)")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def force_potd(self, interaction: discord.Interaction):
    #     await interaction.response.defer()
        
    #     # Fetch next available batch
    #     batch = await self.db_manager.get_next_queue_batch()
        
    #     if not batch:
    #         await interaction.followup.send("⚠️ Queue is empty! No unused problems found in DB.")
    #         return

    #     await self._post_daily_batch(batch)
    #     await interaction.followup.send("✅ Daily job triggered successfully.")

    # # Note: 'remove_potd' removed from here because it exists in cogs/problems.py

    # ==================== Scheduled Task ====================

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=IST))
    async def daily_problem_post(self):
        """Runs automatically at midnight IST."""
        logger.info("Running daily DB queue task...")
        
        try:
            # 1. Check if POTD already set for today?
            # For now, we assume if the task runs, we post.
            
            # 2. Fetch and Post
            batch = await self.db_manager.get_next_queue_batch()
            
            if batch:
                await self._post_daily_batch(batch)
            else:
                logger.error("Daily task failed: Queue is empty!")
                
        except Exception as e:
            logger.error(f"Critical error in daily task: {e}", exc_info=True)

    @daily_problem_post.before_loop
    async def before_daily_post(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
    logger.info("SchedulerCog (DB Queue) loaded")