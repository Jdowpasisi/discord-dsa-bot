"""
Help Cog - Display all available commands with descriptions
"""

import discord
from discord import app_commands
from discord.ext import commands
import config


class HelpCog(commands.Cog):
    """Cog for displaying help information about all available commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(
        name="help",
        description="Display all available bot commands and features"
    )
    async def help_command(self, interaction: discord.Interaction):
        """
        Display comprehensive help information about all available commands
        
        Args:
            interaction: Discord interaction
        """
        embed = discord.Embed(
            title="🤖 LeetCode DSA Bot - Command Help",
            description="Complete guide to all available commands for tracking your coding progress!",
            color=config.COLOR_PRIMARY
        )
        
        # Add bot information
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        # =============== USER PROFILE ===============
        embed.add_field(
            name="👤 `/setup`",
            value=(
                "**Configure your profile**\n"
                "```\n"
                "/setup year:2 leetcode_username:john_doe\n"
                "```\n"
                "• **Parameters:**\n"
                "  - `year`: Your year level (1, 2, 3, 4, or General)\n"
                "  - `leetcode_username`: Your LeetCode username\n"
                "• **Why:** Personalize your profile and track by year\n"
                "• **Note:** Can be run multiple times to update\n"
            ),
            inline=False
        )
        
        # =============== SUBMISSION COMMANDS ===============
        embed.add_field(
            name="📝 `/leetcode_submit`",
            value=(
                "**Submit a completed LeetCode problem**\n"
                "```\n"
                "/leetcode_submit problem_name:two-sum\n"
                "/leetcode_submit problem_name:Two Sum\n"
                "```\n"
                "• **Parameter:**\n"
                "  - `problem_name`: Problem title or slug\n"
                "• **Difficulty:** Auto-detected from LeetCode API\n"
                "• **Points:** Easy=10, Medium=20, Hard=40\n"
                "• **POTD Bonus:** Problem of the Day = 15 pts + bonuses\n"
                "• **Channel:** #dsa or #potd only\n"
                "• **Cooldown:** 30 seconds per user\n"
                "• **Features:** Real-time validation, streak tracking, duplicate prevention\n"
            ),
            inline=False
        )
        
        # =============== STATISTICS COMMANDS ===============
        embed.add_field(
            name="📊 `/stats`",
            value=(
                "**View your statistics and rank**\n"
                "```\n"
                "/stats\n"
                "/stats user:@someone\n"
                "```\n"
                "• **Shows:**\n"
                "  - 🏆 Total Points (all-time)\n"
                "  - 🎖️ Global Rank\n"
                "  - 🔥 Daily Streak\n"
                "  - ⚡ Weekly Streak\n"
                "  - 📅 Last Submission\n"
                "  - 👤 LeetCode Username (if set)\n"
                "  - 📚 Year Level (if set)\n"
                "• **Optional:** View another user's stats\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 `/leaderboard`",
            value=(
                "**View the leaderboard**\n"
                "```\n"
                "/leaderboard\n"
                "/leaderboard period:weekly\n"
                "/leaderboard period:monthly\n"
                "```\n"
                "• **Periods:**\n"
                "  - `weekly`: Monday-Sunday (default)\n"
                "  - `monthly`: 1st-last day of month\n"
                "• **Shows:**\n"
                "  - 🥇🥈🥉 Top 5 performers\n"
                "  - Period-specific points\n"
                "  - Total submission count\n"
                "  - Inactive members count\n"
            ),
            inline=False
        )
        
        # =============== PROBLEM COMMANDS ===============
        embed.add_field(
            name="📚 Problem Commands",
            value=(
                "**`/daily`** - View today's Problem of the Day\n"
                "**`/problem <name>`** - Get details about a specific problem\n"
                "• Shows difficulty, topic, and submission status\n"
            ),
            inline=False
        )
        
        # =============== AUTOMATED FEATURES ===============
        embed.add_field(
            name="🤖 Automated Features",
            value=(
                "The bot automatically:\n"
                "• **Daily Problems** (12:00 AM)\n"
                "  - Posts 3 problems (Easy, Medium, Hard)\n"
                "  - Rotates through 6 topics weekly\n"
                "  - Sunday: Revision from previous topics\n"
                "\n"
                "• **Weekly Leaderboard** (Sunday 11:59 PM)\n"
                "  - Posts top 5 performers\n"
                "  - Announces weekly champion\n"
                "  - Tracks inactive members\n"
                "\n"
                "• **Monthly Leaderboard** (1st of month)\n"
                "  - Reviews previous month\n"
                "  - Celebrates monthly champion\n"
                "  - Resets for new month\n"
            ),
            inline=False
        )
        
        # =============== POINTS & STREAKS ===============
        embed.add_field(
            name="⭐ Points & Streaks",
            value=(
                "**Point System:**\n"
                "• Easy: 10 points\n"
                "• Medium: 20 points\n"
                "• Hard: 40 points\n"
                "• 🏆 **POTD Bonus:** 15 points (fixed, plus bonuses)\n"
                "\n"
                "**Streak Bonuses:**\n"
                "• 🔥 **Daily Streak:** +5 points (submit every day)\n"
                "• ⚡ **Weekly Streak:** +20 points (submit every week)\n"
                "• Breaks if you miss a day/week\n"
                "• Displayed in `/stats`\n"
            ),
            inline=True
        )
        
        # =============== RULES & RESTRICTIONS ===============
        embed.add_field(
            name="📋 Rules",
            value=(
                "**Submission Rules:**\n"
                "• One submission per problem (no duplicates)\n"
                "• Difficulty auto-detected (no need to specify!)\n"
                "• 30-second cooldown between submissions\n"
                "• Only in #dsa or #potd channels\n"
                "• Real-time LeetCode API validation\n"
                "\n"
                "**Problem Format:**\n"
                "• Use problem slug: `two-sum`\n"
                "• Or title with spaces: `Two Sum`\n"
                "• Case-insensitive\n"
            ),
            inline=True
        )
        
        # =============== FOOTER ===============
        embed.set_footer(
            text="💡 Tips: /setup to configure profile | /daily for today's POTD | Leaderboard updates Sunday nights",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    """Load the HelpCog"""
    await bot.add_cog(HelpCog(bot))
