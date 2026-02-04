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
        logger.info("="*60)
        logger.info("✅ SchedulerCog (DB Queue Mode) initialized")
        logger.info(f"Scheduler task started: {self.daily_problem_post.is_running()}")
        logger.info(f"Scheduled time: 12:00 AM IST (00:00 IST)")
        logger.info(f"Current time (IST): {datetime.now(IST).strftime('%Y-%m-%d %I:%M:%S %p')}")
        logger.info(f"Current time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')}")
        logger.info("="*60)
        logger.info(f"Scheduler task started: {self.daily_problem_post.is_running()}")
        logger.info(f"Scheduled time: 12:00 AM IST (00:00 IST)")
        logger.info(f"Current time (IST): {datetime.now(IST).strftime('%Y-%m-%d %I:%M:%S %p')}")
        logger.info(f"Current time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')}")
        logger.info("="*60)
    
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

        # 3. Post
        channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
        if not channel:
            logger.error(f"Channel #{self.CHANNEL_NAME} not found.")
            raise ValueError(f"Channel #{self.CHANNEL_NAME} not found in any server")
        
        # Verify it's a text channel
        if not isinstance(channel, discord.TextChannel):
            logger.error(f"Channel #{self.CHANNEL_NAME} is not a text channel (type: {type(channel).__name__})")
            raise TypeError(f"Channel must be a text channel")
        
        # Check permissions
        perms = channel.permissions_for(channel.guild.me)
        logger.info(f"Bot permissions in #{self.CHANNEL_NAME}: Send Messages={perms.send_messages}, Embed Links={perms.embed_links}, View Channel={perms.view_channel}, Manage Messages={perms.manage_messages}")
        
        missing_perms = []
        if not perms.view_channel:
            missing_perms.append("View Channel")
        if not perms.send_messages:
            missing_perms.append("Send Messages")
        if not perms.embed_links:
            missing_perms.append("Embed Links")
        if not perms.manage_messages:
            missing_perms.append("Manage Messages")
        
        if missing_perms:
            error_msg = f"Missing permissions in #{self.CHANNEL_NAME}: {', '.join(missing_perms)}"
            logger.error(error_msg)
            raise PermissionError(error_msg)
        
        # Send the message
        try:
            message = await channel.send(embed=embed)
            logger.info(f"Successfully posted to #{self.CHANNEL_NAME}")
            
            # Pin the POTD message
            await message.pin()
            logger.info(f"Successfully pinned POTD message (ID: {message.id})")
            
            # Optional: Unpin old POTD messages to keep only the latest one pinned
            # This removes the "X pinned a message" system notification
            pins = await channel.pins()
            for pin in pins:
                # Unpin old POTD messages (skip the one we just pinned)
                if pin.id != message.id and pin.author.id == self.bot.user.id and pin.embeds:
                    # Check if it's a POTD message
                    if pin.embeds[0].title and "Problem of the Day" in pin.embeds[0].title:
                        await pin.unpin()
                        logger.info(f"Unpinned old POTD message (ID: {pin.id})")
            
        except discord.errors.Forbidden as e:
            logger.error(f"Forbidden error despite permission check: {e}. Channel ID: {channel.id}, Guild: {channel.guild.name}")
            raise

    # ==================== Admin Commands ====================

    @app_commands.command(name="check_permissions", description="Admin: Check bot permissions in #potd channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def check_permissions(self, interaction: discord.Interaction):
        """Diagnostic command to check bot permissions."""
        await interaction.response.defer(ephemeral=True)
        
        channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
        
        if not channel:
            await interaction.followup.send(f"❌ Channel #{self.CHANNEL_NAME} not found in any server!")
            return
        
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(f"❌ #{self.CHANNEL_NAME} exists but is not a text channel (type: {type(channel).__name__})")
            return
        
        perms = channel.permissions_for(channel.guild.me)
        
        status = [
            f"**Server:** {channel.guild.name}",
            f"**Channel:** #{channel.name} (ID: {channel.id})",
            f"**Bot:** {channel.guild.me.name}",
            f"**Bot Role:** {channel.guild.me.top_role.name}\n",
            f"**Permissions:**",
            f"✅ View Channel" if perms.view_channel else "❌ View Channel",
            f"✅ Send Messages" if perms.send_messages else "❌ Send Messages",
            f"✅ Embed Links" if perms.embed_links else "❌ Embed Links",
            f"✅ Read Message History" if perms.read_message_history else "❌ Read Message History",
            f"✅ Manage Messages" if perms.manage_messages else "❌ Manage Messages",
        ]
        
        all_good = perms.view_channel and perms.send_messages and perms.embed_links and perms.manage_messages
        
        if all_good:
            status.append("\n✅ **All required permissions are granted!**")
        else:
            status.append("\n⚠️ **Missing required permissions! Fix these in channel settings.**")
        
        await interaction.followup.send("\n".join(status))
    
    @app_commands.command(name="force_potd", description="Admin: Trigger daily job immediately (Consumes Queue)")
    @app_commands.checks.has_permissions(administrator=True)
    async def force_potd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Fetch next available batch
        batch = await self.db_manager.get_next_queue_batch()
        
        if not batch:
            await interaction.followup.send("⚠️ Queue is empty! No unused problems found in DB.")
            return

        try:
            await self._post_daily_batch(batch)
            await interaction.followup.send("✅ Daily job triggered successfully.")
        except discord.errors.Forbidden as e:
            await interaction.followup.send(f"❌ Permission error: {e}\n\nUse `/check_permissions` to diagnose the issue.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")
            raise
    
    @app_commands.command(name="preview_potd", description="Admin: Preview what would be posted next (doesn't update DB)")
    @app_commands.checks.has_permissions(administrator=True)
    async def preview_potd(self, interaction: discord.Interaction):
        """Preview the next POTD batch without consuming it or updating the database"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Fetch next available batch
            batch = await self.db_manager.get_next_queue_batch()
            
            if not batch:
                await interaction.followup.send("⚠️ Queue is empty! No unused problems found in DB.")
                return
            
            # Create preview embed
            embed = discord.Embed(
                title="📋 Next POTD Preview (Test)",
                description="This is what would be posted next. Database will NOT be updated.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            sorted_years = sorted(batch.keys())
            
            for year in sorted_years:
                p = batch[year]
                safe_url = generate_problem_url(p['platform'], p['slug'])
                difficulty = p.get('difficulty', 'Medium')
                
                embed.add_field(
                    name=f"🔹 Year {year} ({difficulty}) - {p['platform']}",
                    value=f"**{p['title']}**\n[Solve Here]({safe_url})",
                    inline=False
                )
            
            embed.set_footer(text="Use /force_potd to post this batch and mark as POTD")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")
            raise
    
    @app_commands.command(name="scheduler_status", description="Admin: Check if the scheduler is running")
    @app_commands.checks.has_permissions(administrator=True)
    async def scheduler_status(self, interaction: discord.Interaction):
        """Check the status of the daily scheduler"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            is_running = self.daily_problem_post.is_running()
            next_iteration = self.daily_problem_post.next_iteration
            
            embed = discord.Embed(
                title="📅 Scheduler Status",
                color=discord.Color.green() if is_running else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Status",
                value="✅ Running" if is_running else "❌ Not Running",
                inline=False
            )
            
            if next_iteration:
                # Convert next_iteration to IST
                next_run_ist = next_iteration.astimezone(IST)
                embed.add_field(
                    name="Next Run (IST)",
                    value=f"{next_run_ist.strftime('%Y-%m-%d %I:%M:%S %p')}",
                    inline=False
                )
                
                # Time until next run
                time_until = next_iteration - datetime.now(timezone.utc)
                hours, remainder = divmod(int(time_until.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                embed.add_field(
                    name="Time Until Next Run",
                    value=f"{hours}h {minutes}m {seconds}s",
                    inline=False
                )
            
            embed.add_field(
                name="Scheduled Time",
                value="12:00 AM IST (Daily)",
                inline=False
            )
            
            embed.set_footer(text="Use /preview_potd to see what will be posted next")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")
            raise

    # # Note: 'remove_potd' removed from here because it exists in cogs/problems.py

    # ==================== Scheduled Task ====================

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=IST))
    async def daily_problem_post(self):
        """Runs automatically at midnight IST."""
        logger.info("="*60)
        logger.info("🔔 SCHEDULER TRIGGERED: Running daily DB queue task...")
        logger.info(f"Current time (UTC): {datetime.now(timezone.utc)}")
        logger.info(f"Current time (IST): {datetime.now(IST)}")
        logger.info("="*60)
        
        try:
            # 1. Clear old POTDs (from previous days)
            today_str = datetime.now().date().isoformat()
            logger.info(f"Clearing old POTDs before {today_str}...")
            await self.db_manager.clear_old_potd(today_str)
            logger.info(f"✅ Cleared old POTDs before {today_str}")
            
            # 2. Fetch and Post
            logger.info("Fetching next queue batch...")
            batch = await self.db_manager.get_next_queue_batch()
            
            if batch:
                logger.info(f"✅ Fetched batch with {len(batch)} problems")
                await self._post_daily_batch(batch)
                logger.info("✅ Daily POTD posted successfully!")
            else:
                logger.error("❌ Daily task failed: Queue is empty!")
                
        except Exception as e:
            logger.error(f"❌ Critical error in daily task: {e}", exc_info=True)

    @daily_problem_post.before_loop
    async def before_daily_post(self):
        logger.info("⏳ Scheduler waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        logger.info("✅ Bot is ready! Scheduler will run at next scheduled time.")
        next_run = self.daily_problem_post.next_iteration
        if next_run:
            next_run_ist = next_run.astimezone(IST)
            logger.info(f"📅 Next scheduled run: {next_run_ist.strftime('%Y-%m-%d %I:%M:%S %p IST')}")
        else:
            logger.warning("⚠️ Next iteration time not available yet")
    
    @daily_problem_post.error
    async def daily_problem_post_error(self, error: Exception):
        """Handle errors in the scheduler task"""
        logger.error("="*60)
        logger.error("❌ SCHEDULER ERROR OCCURRED")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Error message: {error}")
        logger.error("="*60, exc_info=True)
        # Don't stop the scheduler - let it retry next time

async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
    logger.info("✅ SchedulerCog (DB Queue) loaded successfully")