"""
StatsCog: User statistics, leaderboards, and automated weekly/monthly reports.

This cog handles:
- /stats command: Show individual user statistics
- /leaderboard command: Weekly/monthly leaderboards
- Automated weekly leaderboard (Sunday 11:59 PM)
- Automated monthly leaderboard (1st of month)
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
from typing import Literal, Optional, List, Tuple
import logging
import calendar

from database.manager import DatabaseManager
import config

logger = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    """Cog for user statistics and leaderboards with automation"""
    
    LEADERBOARD_CHANNEL = "dsa"
    TOP_USERS_COUNT = 5
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_manager: DatabaseManager = bot.db
        
        # Start automated tasks
        self.weekly_leaderboard_post.start()
        self.monthly_leaderboard_post.start()
        logger.info("StatsCog initialized - automated tasks started")
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.weekly_leaderboard_post.cancel()
        self.monthly_leaderboard_post.cancel()
        logger.info("StatsCog unloaded - automated tasks cancelled")
    
    # ==================== Helper Methods ====================
    
    def _get_week_range(self) -> Tuple[datetime, datetime]:
        """Get current week's Monday-Sunday date range."""
        today = datetime.now()
        # Monday = 0, Sunday = 6
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        # Set to start/end of day
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return monday, sunday
    
    def _get_month_range(self) -> Tuple[datetime, datetime]:
        """Get current month's date range."""
        today = datetime.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Last day of month
        last_day_num = calendar.monthrange(today.year, today.month)[1]
        last_day = today.replace(day=last_day_num, hour=23, minute=59, second=59, microsecond=999999)
        
        return first_day, last_day
    
    async def _get_user_rank(self, discord_id: int) -> Optional[int]:
        """Get user's rank based on total points."""
        try:
            async with self.db_manager.db.execute(
                """
                SELECT discord_id, 
                       ROW_NUMBER() OVER (ORDER BY total_points DESC) as rank
                FROM Users
                """
            ) as cursor:
                rows = await cursor.fetchall()
                
                for row in rows:
                    if row[0] == discord_id:
                        return row[1]
                
                return None
        except Exception as e:
            logger.error(f"Failed to get user rank: {e}")
            return None
    
    async def _get_weekly_leaderboard(self) -> List[dict]:
        """
        Get weekly leaderboard (Monday-Sunday).
        Returns list of dicts with user data and weekly points.
        """
        monday, sunday = self._get_week_range()
        
        try:
            async with self.db_manager.db.execute(
                """
                SELECT 
                    u.discord_id,
                    u.total_points,
                    u.daily_streak,
                    u.weekly_streak,
                    COALESCE(SUM(s.points_awarded), 0) as weekly_points,
                    COUNT(s.submission_id) as weekly_submissions
                FROM Users u
                LEFT JOIN Submissions s 
                    ON u.discord_id = s.discord_id 
                    AND s.submission_date BETWEEN ? AND ?
                GROUP BY u.discord_id
                ORDER BY weekly_points DESC, u.total_points DESC
                """,
                (monday.date(), sunday.date())
            ) as cursor:
                rows = await cursor.fetchall()
                
                leaderboard = []
                for row in rows:
                    leaderboard.append({
                        'discord_id': row[0],
                        'total_points': row[1],
                        'daily_streak': row[2],
                        'weekly_streak': row[3],
                        'weekly_points': row[4],
                        'weekly_submissions': row[5]
                    })
                
                return leaderboard
        except Exception as e:
            logger.error(f"Failed to get weekly leaderboard: {e}")
            return []
    
    async def _get_monthly_leaderboard(self) -> List[dict]:
        """
        Get monthly leaderboard (1st-last day of month).
        Returns list of dicts with user data and monthly points.
        """
        first_day, last_day = self._get_month_range()
        
        try:
            async with self.db_manager.db.execute(
                """
                SELECT 
                    u.discord_id,
                    u.total_points,
                    u.daily_streak,
                    u.weekly_streak,
                    COALESCE(SUM(s.points_awarded), 0) as monthly_points,
                    COUNT(s.submission_id) as monthly_submissions
                FROM Users u
                LEFT JOIN Submissions s 
                    ON u.discord_id = s.discord_id 
                    AND s.submission_date BETWEEN ? AND ?
                GROUP BY u.discord_id
                ORDER BY monthly_points DESC, u.total_points DESC
                """,
                (first_day.date(), last_day.date())
            ) as cursor:
                rows = await cursor.fetchall()
                
                leaderboard = []
                for row in rows:
                    leaderboard.append({
                        'discord_id': row[0],
                        'total_points': row[1],
                        'daily_streak': row[2],
                        'weekly_streak': row[3],
                        'monthly_points': row[4],
                        'monthly_submissions': row[5]
                    })
                
                return leaderboard
        except Exception as e:
            logger.error(f"Failed to get monthly leaderboard: {e}")
            return []
    
    def _create_stats_embed(
        self,
        user: discord.User,
        stats: dict,
        rank: Optional[int]
    ) -> discord.Embed:
        """Create rich embed for user stats."""
        embed = discord.Embed(
            title=f"📊 Stats for {user.display_name}",
            color=config.COLOR_SUCCESS,
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Total Points
        embed.add_field(
            name="🏆 Total Points",
            value=f"**{stats.get('total_points', 0)}** points",
            inline=True
        )
        
        # Rank
        if rank:
            embed.add_field(
                name="🎖️ Rank",
                value=f"**#{rank}**",
                inline=True
            )
        
        # Spacer for layout
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        # Daily Streak
        daily_streak = stats.get('daily_streak', 0)
        daily_emoji = "🔥" if daily_streak > 0 else "❄️"
        embed.add_field(
            name=f"{daily_emoji} Daily Streak",
            value=f"**{daily_streak}** day{'s' if daily_streak != 1 else ''}",
            inline=True
        )
        
        # Weekly Streak
        weekly_streak = stats.get('weekly_streak', 0)
        weekly_emoji = "⚡" if weekly_streak > 0 else "💤"
        embed.add_field(
            name=f"{weekly_emoji} Weekly Streak",
            value=f"**{weekly_streak}** week{'s' if weekly_streak != 1 else ''}",
            inline=True
        )
        
        # Last Submission
        last_submission = stats.get('last_submission_date')
        if last_submission:
            try:
                if isinstance(last_submission, str):
                    last_date = datetime.fromisoformat(last_submission)
                else:
                    last_date = last_submission
                
                days_ago = (datetime.now() - last_date).days
                if days_ago == 0:
                    last_sub_text = "Today! 🎯"
                elif days_ago == 1:
                    last_sub_text = "Yesterday"
                else:
                    last_sub_text = f"{days_ago} days ago"
            except:
                last_sub_text = "Unknown"
        else:
            last_sub_text = "Never"
        
        embed.add_field(
            name="📅 Last Submission",
            value=last_sub_text,
            inline=True
        )
        
        embed.set_footer(text="Keep grinding! 💪")
        
        return embed
    
    def _create_leaderboard_embed(
        self,
        leaderboard: List[dict],
        period: str,
        guild: discord.Guild
    ) -> discord.Embed:
        """Create rich embed for leaderboard."""
        if period == "weekly":
            monday, sunday = self._get_week_range()
            title = f"🏆 Weekly Leaderboard"
            description = f"**{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}**\n"
            points_key = 'weekly_points'
            submissions_key = 'weekly_submissions'
        else:  # monthly
            first_day, last_day = self._get_month_range()
            title = f"🏆 Monthly Leaderboard"
            description = f"**{first_day.strftime('%B %Y')}**\n"
            points_key = 'monthly_points'
            submissions_key = 'monthly_submissions'
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=config.COLOR_PRIMARY,
            timestamp=datetime.now()
        )
        
        # Top performers
        top_users = [u for u in leaderboard if u[points_key] > 0][:self.TOP_USERS_COUNT]
        
        if top_users:
            medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            leaderboard_text = ""
            for i, user_data in enumerate(top_users):
                member = guild.get_member(user_data['discord_id'])
                username = member.display_name if member else f"User {user_data['discord_id']}"
                
                medal = medal_emojis[i] if i < len(medal_emojis) else f"{i+1}."
                points = user_data[points_key]
                submissions = user_data[submissions_key]
                
                leaderboard_text += (
                    f"{medal} **{username}**\n"
                    f"   • {points} points | {submissions} submission{'s' if submissions != 1 else ''}\n"
                )
            
            embed.add_field(
                name="🌟 Top Performers",
                value=leaderboard_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🌟 Top Performers",
                value="*No submissions yet this period*",
                inline=False
            )
        
        # Inactive users (0 submissions)
        inactive_users = [u for u in leaderboard if u[points_key] == 0]
        
        if inactive_users:
            if len(inactive_users) <= 10:
                inactive_text = ""
                for user_data in inactive_users[:10]:
                    member = guild.get_member(user_data['discord_id'])
                    if member:
                        inactive_text += f"• {member.display_name}\n"
            else:
                inactive_text = f"*{len(inactive_users)} members with 0 submissions*\n"
                inactive_text += "Get started with `/submit` to join the leaderboard!"
            
            embed.add_field(
                name="💤 Inactive This Period",
                value=inactive_text if inactive_text else "*None - Great job everyone!*",
                inline=False
            )
        
        embed.set_footer(text="Use /stats to see your personal statistics")
        
        return embed
    
    async def _post_to_channel(self, embed: discord.Embed, channel_name: str) -> bool:
        """Post embed to specified channel."""
        try:
            channel = discord.utils.get(
                self.bot.get_all_channels(),
                name=channel_name
            )
            
            if not channel:
                logger.error(f"Channel '{channel_name}' not found")
                return False
            
            await channel.send(embed=embed)
            logger.info(f"Posted to #{channel_name}")
            return True
            
        except discord.Forbidden:
            logger.error(f"No permission to post in #{channel_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
            return False
    
    # ==================== Slash Commands ====================
    
    @app_commands.command(
        name="stats",
        description="View your LeetCode submission statistics"
    )
    @app_commands.describe(
        user="User to view stats for (defaults to yourself)"
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None
    ):
        """
        Display user statistics including points, streaks, and rank.
        
        Args:
            interaction: Discord interaction
            user: Optional user to view (defaults to command user)
        """
        await interaction.response.defer()
        
        target_user = user or interaction.user
        discord_id = target_user.id
        
        try:
            # Get user stats from database
            user_data = await self.db_manager.get_user(discord_id)
            
            if not user_data:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ User Not Found",
                        description=(
                            f"{target_user.mention} hasn't submitted any problems yet.\n\n"
                            f"Use `/submit` to get started!"
                        ),
                        color=config.COLOR_ERROR
                    )
                )
                return
            
            # Get user's rank
            rank = await self._get_user_rank(discord_id)
            
            # Create and send embed
            embed = self._create_stats_embed(target_user, user_data, rank)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}", exc_info=True)
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve statistics. Please try again later.",
                    color=config.COLOR_ERROR
                )
            )
    
    @app_commands.command(
        name="leaderboard",
        description="View the leaderboard for weekly or monthly submissions"
    )
    @app_commands.describe(
        period="Time period for leaderboard (weekly by default)"
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        period: Literal["weekly", "monthly"] = "weekly"
    ):
        """
        Display leaderboard for specified period.
        
        Args:
            interaction: Discord interaction
            period: "weekly" (Monday-Sunday) or "monthly" (1st-last day)
        """
        await interaction.response.defer()
        
        try:
            # Get leaderboard data
            if period == "weekly":
                leaderboard_data = await self._get_weekly_leaderboard()
            else:
                leaderboard_data = await self._get_monthly_leaderboard()
            
            if not leaderboard_data:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="📊 Leaderboard",
                        description="No users found. Start submitting with `/submit`!",
                        color=config.COLOR_WARNING
                    )
                )
                return
            
            # Create and send embed
            embed = self._create_leaderboard_embed(
                leaderboard_data,
                period,
                interaction.guild
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve leaderboard. Please try again later.",
                    color=config.COLOR_ERROR
                )
            )
    
    # ==================== Automated Tasks ====================
    
    @tasks.loop(time=time(hour=23, minute=59))  # Sunday 11:59 PM
    async def weekly_leaderboard_post(self):
        """
        Automated weekly leaderboard post every Sunday at 11:59 PM.
        
        Posts:
        - Top 5 users by weekly points
        - List of inactive users (0 submissions)
        - Weekly winner announcement
        """
        try:
            today = datetime.now()
            
            # Only run on Sundays (weekday 6)
            if today.weekday() != 6:
                return
            
            logger.info("Starting automated weekly leaderboard post")
            
            # Get weekly leaderboard
            leaderboard_data = await self._get_weekly_leaderboard()
            
            if not leaderboard_data:
                logger.warning("No leaderboard data available")
                return
            
            # Find weekly winner
            winner = next((u for u in leaderboard_data if u['weekly_points'] > 0), None)
            
            # Create embed
            monday, sunday = self._get_week_range()
            
            embed = discord.Embed(
                title="🎉 Weekly Leaderboard Results!",
                description=f"**Week of {monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}**\n",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            # Announce winner
            if winner:
                # Get member object for mention
                for guild in self.bot.guilds:
                    member = guild.get_member(winner['discord_id'])
                    if member:
                        winner_name = member.mention
                        break
                else:
                    winner_name = f"User {winner['discord_id']}"
                
                embed.add_field(
                    name="👑 Weekly Champion",
                    value=(
                        f"**{winner_name}**\n"
                        f"🏆 {winner['weekly_points']} points this week\n"
                        f"📝 {winner['weekly_submissions']} submissions\n"
                        f"💪 Keep up the great work!"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="👑 Weekly Champion",
                    value="*No submissions this week. Be the first next week!*",
                    inline=False
                )
            
            # Top performers
            top_users = [u for u in leaderboard_data if u['weekly_points'] > 0][:self.TOP_USERS_COUNT]
            
            if len(top_users) > 1:
                medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                leaderboard_text = ""
                
                for i, user_data in enumerate(top_users):
                    # Get member object
                    member = None
                    for guild in self.bot.guilds:
                        member = guild.get_member(user_data['discord_id'])
                        if member:
                            break
                    
                    username = member.display_name if member else f"User {user_data['discord_id']}"
                    medal = medal_emojis[i] if i < len(medal_emojis) else f"{i+1}."
                    
                    leaderboard_text += (
                        f"{medal} **{username}** - {user_data['weekly_points']} pts "
                        f"({user_data['weekly_submissions']} problems)\n"
                    )
                
                embed.add_field(
                    name="🌟 Top 5 This Week",
                    value=leaderboard_text,
                    inline=False
                )
            
            # Inactive users
            inactive_users = [u for u in leaderboard_data if u['weekly_points'] == 0]
            
            if inactive_users:
                inactive_count = len(inactive_users)
                embed.add_field(
                    name="⚠️ Inactive Members",
                    value=(
                        f"**{inactive_count}** member{'s' if inactive_count != 1 else ''} "
                        f"had 0 submissions this week.\n"
                        f"Don't fall behind! Use `/submit` to join the competition."
                    ),
                    inline=False
                )
            
            embed.set_footer(text="New week starts Monday! Good luck! 🚀")
            
            # Post to channel
            success = await self._post_to_channel(embed, self.LEADERBOARD_CHANNEL)
            
            if success:
                logger.info("✅ Weekly leaderboard posted successfully")
            else:
                logger.error("Failed to post weekly leaderboard")
                
        except Exception as e:
            logger.error(f"Error in weekly_leaderboard_post: {e}", exc_info=True)
    
    @weekly_leaderboard_post.before_loop
    async def before_weekly_post(self):
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()
        logger.info("Bot ready - weekly leaderboard task will begin")
    
    @tasks.loop(time=time(hour=0, minute=0))  # Midnight
    async def monthly_leaderboard_post(self):
        """
        Automated monthly leaderboard post on 1st of each month at midnight.
        
        Posts:
        - Top 5 users by monthly points
        - Monthly winner announcement
        - Inactive user count
        """
        try:
            today = datetime.now()
            
            # Only run on 1st of month
            if today.day != 1:
                return
            
            logger.info("Starting automated monthly leaderboard post")
            
            # Get monthly leaderboard (for previous month)
            # Calculate previous month range
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year
            
            first_day = datetime(prev_year, prev_month, 1, 0, 0, 0)
            last_day_num = calendar.monthrange(prev_year, prev_month)[1]
            last_day = datetime(prev_year, prev_month, last_day_num, 23, 59, 59)
            
            # Query database for previous month
            leaderboard_data = []
            try:
                async with self.db_manager.db.execute(
                    """
                    SELECT 
                        u.discord_id,
                        u.total_points,
                        COALESCE(SUM(s.points_awarded), 0) as monthly_points,
                        COUNT(s.submission_id) as monthly_submissions
                    FROM Users u
                    LEFT JOIN Submissions s 
                        ON u.discord_id = s.discord_id 
                        AND s.submission_date BETWEEN ? AND ?
                    GROUP BY u.discord_id
                    ORDER BY monthly_points DESC, u.total_points DESC
                    """,
                    (first_day.date(), last_day.date())
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    for row in rows:
                        leaderboard_data.append({
                            'discord_id': row[0],
                            'total_points': row[1],
                            'monthly_points': row[2],
                            'monthly_submissions': row[3]
                        })
            except Exception as e:
                logger.error(f"Failed to query monthly leaderboard: {e}")
                return
            
            if not leaderboard_data:
                logger.warning("No leaderboard data available for previous month")
                return
            
            # Find monthly winner
            winner = next((u for u in leaderboard_data if u['monthly_points'] > 0), None)
            
            # Create embed
            month_name = first_day.strftime('%B %Y')
            
            embed = discord.Embed(
                title="🏆 Monthly Leaderboard Results!",
                description=f"**{month_name}**\n",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            
            # Announce winner
            if winner:
                # Get member object for mention
                for guild in self.bot.guilds:
                    member = guild.get_member(winner['discord_id'])
                    if member:
                        winner_name = member.mention
                        break
                else:
                    winner_name = f"User {winner['discord_id']}"
                
                embed.add_field(
                    name="👑 Monthly Champion",
                    value=(
                        f"**{winner_name}**\n"
                        f"🏆 {winner['monthly_points']} points in {month_name}\n"
                        f"📝 {winner['monthly_submissions']} submissions\n"
                        f"🎉 Congratulations!"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="👑 Monthly Champion",
                    value=f"*No submissions in {month_name}.*",
                    inline=False
                )
            
            # Top performers
            top_users = [u for u in leaderboard_data if u['monthly_points'] > 0][:self.TOP_USERS_COUNT]
            
            if len(top_users) > 1:
                medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                leaderboard_text = ""
                
                for i, user_data in enumerate(top_users):
                    # Get member object
                    member = None
                    for guild in self.bot.guilds:
                        member = guild.get_member(user_data['discord_id'])
                        if member:
                            break
                    
                    username = member.display_name if member else f"User {user_data['discord_id']}"
                    medal = medal_emojis[i] if i < len(medal_emojis) else f"{i+1}."
                    
                    leaderboard_text += (
                        f"{medal} **{username}** - {user_data['monthly_points']} pts "
                        f"({user_data['monthly_submissions']} problems)\n"
                    )
                
                embed.add_field(
                    name="🌟 Top 5 This Month",
                    value=leaderboard_text,
                    inline=False
                )
            
            # Inactive users
            inactive_users = [u for u in leaderboard_data if u['monthly_points'] == 0]
            
            if inactive_users:
                inactive_count = len(inactive_users)
                embed.add_field(
                    name="📊 Activity Summary",
                    value=(
                        f"**{inactive_count}** member{'s' if inactive_count != 1 else ''} "
                        f"had 0 submissions last month.\n"
                        f"New month, new opportunities! Start grinding today! 💪"
                    ),
                    inline=False
                )
            
            embed.set_footer(text="Let's make this month count! 🚀")
            
            # Post to channel
            success = await self._post_to_channel(embed, self.LEADERBOARD_CHANNEL)
            
            if success:
                logger.info("✅ Monthly leaderboard posted successfully")
            else:
                logger.error("Failed to post monthly leaderboard")
                
        except Exception as e:
            logger.error(f"Error in monthly_leaderboard_post: {e}", exc_info=True)
    
    @monthly_leaderboard_post.before_loop
    async def before_monthly_post(self):
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()
        logger.info("Bot ready - monthly leaderboard task will begin")
    
    # ==================== Legacy Prefix Commands ====================
    
    @commands.command(name="mystats")
    async def mystats_legacy(self, ctx: commands.Context):
        """Legacy command: View your stats (use /stats instead)"""
        await ctx.send(
            "ℹ️ This command is deprecated. Please use `/stats` instead for a better experience!"
        )


async def setup(bot: commands.Bot):
    """Load the StatsCog."""
    await bot.add_cog(StatsCog(bot))
    logger.info("StatsCog loaded successfully")
