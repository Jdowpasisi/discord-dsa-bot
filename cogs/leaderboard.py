"""
Leaderboard Cog - Display rankings and statistics
"""

import discord 
from discord import app_commands
from discord.ext import commands
import config


class Leaderboard(commands.Cog):
    """Commands for viewing leaderboards and rankings"""
    
    def __init__(self, bot):
        self.bot = bot

    # ==================== Slash Commands ====================
        
    @app_commands.command(name="leaderboard", description="View the top users by points")
    @app_commands.describe(
        limit="Number of users to show (1-50)",
        period="Time period for leaderboard",
        year="Filter by student year"
    )
    @app_commands.choices(
        period=[
            app_commands.Choice(name="Weekly (Default)", value="weekly"),
            app_commands.Choice(name="Monthly", value="monthly"),
            app_commands.Choice(name="All-Time", value="all-time")
        ],
        year=[
            app_commands.Choice(name="1st Year", value="1"),
            app_commands.Choice(name="2nd Year", value="2"),
            app_commands.Choice(name="3rd Year", value="3"),
            app_commands.Choice(name="4th Year", value="4")
        ]
    )
    async def leaderboard_slash(self, interaction: discord.Interaction, limit: int = None, period: app_commands.Choice[str] = None, year: app_commands.Choice[str] = None):
        """Display the top users by points with optional period and year filters"""
        await interaction.response.defer()
        
        from datetime import datetime, timedelta
        
        if limit is None:
            limit = config.LEADERBOARD_SIZE
        elif limit < 1 or limit > 50:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Invalid Limit",
                    description="Limit must be between 1 and 50",
                    color=config.COLOR_ERROR
                )
            )
            return
            
        # Extract values from Choices
        period_filter = period.value if period else "weekly"
        year_filter = year.value if year else None
        
        # Calculate date range based on period
        now = datetime.now()
        start_date, end_date = None, None
        
        if period_filter == "weekly":
            # Most recent Monday to upcoming Sunday
            days_since_monday = now.weekday()
            start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=6, hours=23, minutes=59, seconds=59))
        elif period_filter == "monthly":
            # First day to last day of current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Get last day of month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            end_date = (next_month - timedelta(seconds=1))
        
        # Get leaderboard data
        leaderboard = await self.bot.db.get_leaderboard(
            limit,
            year=year_filter,
            period=period_filter,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None
        )
        
        if not leaderboard:
            year_text = f"Year {year_filter}" if year_filter else ""
            period_text = f" ({period_filter})" if period_filter != "all-time" else ""
            await interaction.followup.send(
                embed=discord.Embed(
                    title="📭 Empty Leaderboard",
                    description=f"No {year_text}{period_text} submissions yet! Be the first to submit a problem!",
                    color=config.COLOR_INFO
                )
            )
            return
            
        # Build embed with dynamic title
        period_names = {"weekly": "Week", "monthly": "Month", "all-time": "All-Time"}
        period_label = period_names.get(period_filter, "")
        
        if year_filter:
            title = f"🏆 {period_label} Leaderboard (Year {year_filter})"
            description = f"Top Year {year_filter} performers for the {period_label.lower()}"
        else:
            if period_filter == "all-time":
                title = "🏆 Global Leaderboard"
                description = "Top performers ranked by all-time points"
            else:
                title = f"🏆 {period_label} Leaderboard (All Years)"
                description = f"Top performers for {period_label.lower()} period"
        
        if period_filter == "weekly" and start_date:
            description += f"\n📅 {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        elif period_filter == "monthly" and start_date:
            description += f"\n📅 {start_date.strftime('%B %Y')}"
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=config.COLOR_INFO
        )
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, user_data in enumerate(leaderboard, 1):
            try:
                user = await self.bot.fetch_user(user_data["discord_id"])
                user_name = user.display_name if user else f"User {user_data['discord_id']}"
            except:
                user_name = f"User {user_data['discord_id']}"
                
            # Add medal for top 3
            rank_prefix = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
            
            field_value = (
                f"Points: **{user_data['total_points']}**\n"
                f"🔥 Daily: {user_data['daily_streak']} | "
                f"📅 Weekly: {user_data['weekly_streak']}"
            )
            
            embed.add_field(
                name=f"{rank_prefix} {user_name}",
                value=field_value,
                inline=False
            )
            
        embed.set_footer(text=f"Showing top {len(leaderboard)} users")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Leaderboard(bot))
