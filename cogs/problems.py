"""
Problems Cog - Manage and display problems from multiple platforms
PLATFORM-AWARE: All problem operations now include platform context
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import config
from utils.logic import normalize_problem_name, validate_difficulty


class Problems(commands.Cog):
    """Commands for managing and viewing problems"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="addproblem", description="Add a new problem to the database (Admin only)")
    @app_commands.describe(
        problem_slug="Problem slug/ID",
        platform="Platform",
        difficulty="Problem difficulty",
        topic="Problem topic/category"
    )
    @app_commands.choices(
        platform=[
            app_commands.Choice(name="LeetCode", value="LeetCode"),
            app_commands.Choice(name="Codeforces", value="Codeforces"),
            app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
        ],
        difficulty=[
            app_commands.Choice(name="Easy", value="Easy"),
            app_commands.Choice(name="Medium", value="Medium"),
            app_commands.Choice(name="Hard", value="Hard")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_problem(
        self, 
        interaction: discord.Interaction,
        problem_slug: str, 
        platform: app_commands.Choice[str],
        difficulty: app_commands.Choice[str],
        topic: str
    ):
        """
        Add a new problem to the database (Admin only)
        
        Example: /addproblem problem_slug:two-sum platform:LeetCode difficulty:Easy topic:Arrays
        """
        await interaction.response.defer()
        
        try:
            selected_platform = platform.value
            selected_difficulty = difficulty.value
            
            # Normalize problem name for LeetCode
            if selected_platform == "LeetCode":
                problem_slug = normalize_problem_name(problem_slug)
            else:
                problem_slug = problem_slug.strip()
            
            date_posted = datetime.now().date().isoformat()
            
            # ✅ FIXED: Check if problem already exists with platform parameter
            existing = await self.bot.db.get_problem(problem_slug, selected_platform)
            if existing:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="⚠️ Problem Exists",
                        description=f"Problem `{problem_slug}` already exists on {selected_platform}!",
                        color=config.COLOR_WARNING
                    )
                )
                return
            
            # ✅ FIXED: Add problem with platform parameter
            await self.bot.db.create_problem(
                problem_slug=problem_slug,
                platform=selected_platform,
                problem_title=problem_slug.replace("-", " ").title(),
                difficulty=selected_difficulty,
                topic=topic,
                date_posted=date_posted
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Problem Added!",
                description=f"Successfully added `{problem_slug}` to the database",
                color=config.COLOR_SUCCESS
            )
            embed.add_field(name="Platform", value=selected_platform, inline=True)
            embed.add_field(name="Difficulty", value=selected_difficulty, inline=True)
            embed.add_field(name="Topic", value=topic, inline=True)
            embed.add_field(name="Date Posted", value=date_posted, inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in addproblem: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to add problem. Please try again.",
                    color=config.COLOR_ERROR
                )
            )
        
    @app_commands.command(name="problem", description="Get information about a specific problem")
    @app_commands.describe(
        problem_slug="Problem slug/ID",
        platform="Platform (defaults to LeetCode)"
    )
    @app_commands.choices(platform=[
        app_commands.Choice(name="LeetCode", value="LeetCode"),
        app_commands.Choice(name="Codeforces", value="Codeforces"),
        app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
    ])
    async def get_problem_info(
        self, 
        interaction: discord.Interaction,
        problem_slug: str,
        platform: app_commands.Choice[str] = None
    ):
        """
        Get information about a specific problem
        
        Example: /problem problem_slug:two-sum platform:LeetCode
        """
        await interaction.response.defer()
        
        try:
            selected_platform = platform.value if platform else "LeetCode"
            
            # Normalize problem name for LeetCode
            if selected_platform == "LeetCode":
                problem_slug = normalize_problem_name(problem_slug)
            else:
                problem_slug = problem_slug.strip()
            
            # ✅ FIXED: Get problem data with platform parameter
            problem = await self.bot.db.get_problem(problem_slug, selected_platform)
            if not problem:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Problem Not Found",
                        description=f"Problem `{problem_slug}` not found on {selected_platform}.",
                        color=config.COLOR_ERROR
                    )
                )
                return
            
            # Build embed
            title = problem.get("problem_title", problem_slug)
            
            # Generate URL based on platform
            if selected_platform == "LeetCode":
                url = f"https://leetcode.com/problems/{problem_slug}/"
            elif selected_platform == "Codeforces":
                url = f"https://codeforces.com/problemset/problem/{problem_slug}"
            else:  # GeeksforGeeks
                url = f"https://www.geeksforgeeks.org/problems/{problem_slug}/"
            
            embed = discord.Embed(
                title=f"📚 {title}",
                url=url,
                color=config.COLOR_INFO
            )
            
            # Color based on difficulty
            if problem["difficulty"] == "Easy":
                embed.color = 0x00FF00  # Green
            elif problem["difficulty"] == "Medium":
                embed.color = 0xFFAA00  # Orange
            else:  # Hard
                embed.color = 0xFF0000  # Red
            
            embed.add_field(name="Platform", value=selected_platform, inline=True)
            embed.add_field(name="Difficulty", value=problem["difficulty"], inline=True)
            embed.add_field(name="Topic", value=problem["topic"], inline=True)
            
            if problem.get("date_posted"):
                embed.add_field(name="Date Posted", value=problem["date_posted"], inline=True)
                embed.add_field(name="Status", value="🏆 POTD", inline=True)
            else:
                embed.add_field(name="Status", value="⚡ Practice", inline=True)
            
            points = config.POINTS.get(problem['difficulty'], 20)
            embed.add_field(name="Points", value=f"{points} pts", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in problem info: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve problem information.",
                    color=config.COLOR_ERROR
                )
            )
        
    @app_commands.command(name="daily", description="Get today's POTD (if set)")
    async def daily_problem(self, interaction: discord.Interaction):
        """
        Get today's problem (if set by admin)
        
        Usage: /daily
        """
        await interaction.response.defer()
        
        try:
            today_str = datetime.now().date().isoformat()
            
            # Query all platforms for today's POTD
            potd_problems = []
            
            for platform in ["LeetCode", "Codeforces", "GeeksforGeeks"]:
                async with self.bot.db.db.execute(
                    "SELECT problem_slug, problem_title, difficulty, platform FROM Problems WHERE date_posted = ? AND platform = ?",
                    (today_str, platform)
                ) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        potd_problems.append({
                            "slug": row[0],
                            "title": row[1],
                            "difficulty": row[2],
                            "platform": row[3]
                        })
            
            if not potd_problems:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="🌟 Daily Problem",
                        description="No POTD set for today. Check back later!",
                        color=config.COLOR_INFO
                    )
                )
                return
            
            embed = discord.Embed(
                title="🏆 Today's Problem of the Day",
                description=f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
                color=config.COLOR_PRIMARY,
                timestamp=datetime.now()
            )
            
            for problem in potd_problems:
                # Generate URL based on platform
                if problem["platform"] == "LeetCode":
                    url = f"https://leetcode.com/problems/{problem['slug']}/"
                elif problem["platform"] == "Codeforces":
                    url = f"https://codeforces.com/problemset/problem/{problem['slug']}"
                else:
                    url = f"https://www.geeksforgeeks.org/problems/{problem['slug']}/"
                
                embed.add_field(
                    name=f"{problem['difficulty']} - {problem['platform']}",
                    value=f"**{problem['title']}**\n[Solve Here]({url})",
                    inline=False
                )
            
            embed.set_footer(text="Submit with /submit to earn points!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in daily command: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve daily problems.",
                    color=config.COLOR_ERROR
                )
            )


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Problems(bot))