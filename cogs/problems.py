"""
Problems Cog - Manage and display LeetCode problems
"""

import discord
from discord.ext import commands
from datetime import datetime
import config
from utils.logic import normalize_problem_name, validate_difficulty
from utils.logic import normalize_problem_name, validate_difficulty
from utils.logic import normalize_problem_name, validate_difficulty


class Problems(commands.Cog):
    """Commands for managing and viewing problems"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="addproblem", aliases=["addp"])
    @commands.has_permissions(administrator=True)
    async def add_problem(
        self, 
        ctx: commands.Context, 
        problem_slug: str, 
        difficulty: str, 
        topic: str
    ):
        """
        Add a new problem to the database (Admin only)
        
        Usage: !addproblem <problem-slug> <difficulty> <topic>
        Example: !addproblem two-sum Easy Arrays
        """
        # Validate difficulty
        difficulty = difficulty.capitalize()
        if not validate_difficulty(difficulty):
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Invalid Difficulty",
                    description="Difficulty must be: Easy, Medium, or Hard",
                    color=config.COLOR_ERROR
                )
            )
            return
            
        # Normalize problem name
        problem_slug = normalize_problem_name(problem_slug)
        date_posted = datetime.now().date().isoformat()
        
        # Check if problem already exists
        existing = await self.bot.db.get_problem(problem_slug)
        if existing:
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Problem Exists",
                    description=f"Problem `{problem_slug}` already exists in the database!",
                    color=config.COLOR_WARNING
                )
            )
            return
            
        # Add problem
        await self.bot.db.create_problem(
            problem_slug=problem_slug,
            difficulty=difficulty,
            topic=topic,
            date_posted=date_posted
        )
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Problem Added!",
            description=f"Successfully added `{problem_slug}` to the database",
            color=config.COLOR_SUCCESS
        )
        embed.add_field(name="Difficulty", value=difficulty, inline=True)
        embed.add_field(name="Topic", value=topic, inline=True)
        embed.add_field(name="Date Posted", value=date_posted, inline=True)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="problem", aliases=["probleminfo"])
    async def get_problem_info(self, ctx: commands.Context, problem_slug: str):
        """
        Get information about a specific problem
        
        Usage: !problem <problem-slug>
        Example: !problem two-sum
        """
        # Normalize problem name
        problem_slug = normalize_problem_name(problem_slug)
        
        # Get problem data
        problem = await self.bot.db.get_problem(problem_slug)
        if not problem:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Problem Not Found",
                    description=f"Problem `{problem_slug}` not found in the database.",
                    color=config.COLOR_ERROR
                )
            )
            return
            
        # Build embed
        embed = discord.Embed(
            title=f"📝 {problem_slug}",
            url=f"https://leetcode.com/problems/{problem_slug}/",
            color=config.COLOR_INFO
        )
        
        # Color based on difficulty
        if problem["difficulty"] == "Easy":
            embed.color = 0x00FF00  # Green
        elif problem["difficulty"] == "Medium":
            embed.color = 0xFFAA00  # Orange
        else:  # Hard
            embed.color = 0xFF0000  # Red
            
        embed.add_field(name="Difficulty", value=problem["difficulty"], inline=True)
        embed.add_field(name="Topic", value=problem["topic"], inline=True)
        embed.add_field(name="Date Posted", value=problem["date_posted"], inline=True)
        embed.add_field(name="Points", value=f"{config.POINTS[problem['difficulty']]} pts", inline=True)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="daily", aliases=["potd"])
    async def daily_problem(self, ctx: commands.Context):
        """
        Get today's problem (if set by admin)
        
        Usage: !daily
        """
        await ctx.send(
            embed=discord.Embed(
                title="🌟 Daily Problem",
                description="This feature is coming soon! Admins will be able to set a daily problem.",
                color=config.COLOR_INFO
            )
        )


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Problems(bot))
