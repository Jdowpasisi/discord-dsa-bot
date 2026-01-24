"""
Leaderboard Cog - Display rankings and statistics
"""

import discord
from discord.ext import commands
import config


class Leaderboard(commands.Cog):
    """Commands for viewing leaderboards and rankings"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def show_leaderboard(self, ctx: commands.Context, limit: int = None):
        """
        Display the top users by points
        
        Usage: !leaderboard [limit]
        Example: !leaderboard 10
        """
        if limit is None:
            limit = config.LEADERBOARD_SIZE
        elif limit < 1 or limit > 25:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Invalid Limit",
                    description="Limit must be between 1 and 25",
                    color=config.COLOR_ERROR
                )
            )
            return
            
        # Get leaderboard data
        leaderboard = await self.bot.db.get_leaderboard(limit)
        
        if not leaderboard:
            await ctx.send(
                embed=discord.Embed(
                    title="📭 Empty Leaderboard",
                    description="No submissions yet! Be the first to submit a problem!",
                    color=config.COLOR_INFO
                )
            )
            return
            
        # Build embed
        embed = discord.Embed(
            title="🏆 LeetCode Leaderboard",
            description="Top performers ranked by total points",
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
        await ctx.send(embed=embed)
        
    @commands.command(name="rank", aliases=["stats", "profile"])
    async def show_rank(self, ctx: commands.Context, member: discord.Member = None):
        """
        Show detailed stats for a user
        
        Usage: !rank [@user]
        """
        target = member or ctx.author
        discord_id = target.id
        
        # Get user data
        user = await self.bot.db.get_user(discord_id)
        if not user:
            await ctx.send(
                embed=discord.Embed(
                    title="📭 No Data",
                    description=f"{target.display_name} hasn't submitted any problems yet!",
                    color=config.COLOR_INFO
                )
            )
            return
            
        # Get user's rank
        leaderboard = await self.bot.db.get_leaderboard(limit=1000)  # Get all users
        rank = None
        for idx, lb_user in enumerate(leaderboard, 1):
            if lb_user["discord_id"] == discord_id:
                rank = idx
                break
                
        # Build embed
        embed = discord.Embed(
            title=f"📊 Profile - {target.display_name}",
            color=config.COLOR_INFO
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Rank", value=f"**#{rank}**" if rank else "Unranked", inline=True)
        embed.add_field(name="Total Points", value=f"**{user['total_points']}**", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing
        
        embed.add_field(name="🔥 Daily Streak", value=f"**{user['daily_streak']}** days", inline=True)
        embed.add_field(name="📅 Weekly Streak", value=f"**{user['weekly_streak']}** weeks", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        if user["last_submission_date"]:
            from datetime import datetime
            last_sub = datetime.fromisoformat(user["last_submission_date"])
            embed.add_field(
                name="Last Submission",
                value=last_sub.strftime("%B %d, %Y at %I:%M %p"),
                inline=False
            )
            
        await ctx.send(embed=embed)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Leaderboard(bot))
