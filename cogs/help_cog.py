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
            title="🤖 DSA Bot - Complete Command Guide",
            description="Track your coding journey across LeetCode, Codeforces, and GeeksforGeeks!",
            color=config.COLOR_PRIMARY
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        # =============== USER SETUP ===============
        embed.add_field(
            name="👤 User Setup",
            value=(
                "**`/setup`** - Configure your profile\n"
                "• Set year level (1-4) and LeetCode username\n"
                "• Example: `/setup year:2 leetcode_username:john_doe`\n"
                "\n"
                "**`/link`** - Link platform handles\n"
                "• Connect your Codeforces or GeeksforGeeks accounts\n"
                "• Example: `/link platform:codeforces handle:tourist`\n"
            ),
            inline=False
        )
        
        # =============== SUBMISSION ===============
        embed.add_field(
            name="📝 Submission",
            value=(
                "**`/submit`** - Submit a solved problem\n"
                "• **LeetCode:** `/submit problem:two-sum platform:LeetCode`\n"
                "  - Auto-validates via LeetCode API\n"
                "  - Points: Easy=10, Medium=20, Hard=40\n"
                "\n"
                "• **Codeforces:** `/submit problem:1872A platform:Codeforces`\n"
                "  - Use contest+index format (e.g., 1872A)\n"
                "  - Points: based on problem rating\n"
                "\n"
                "• **GeeksforGeeks:** `/submit problem:detect-cycle platform:GeeksforGeeks`\n"
                "  - All GFG problems = Easy (10 points)\n"
                "  - Use problem slug from URL\n"
                "\n"
                "**Bonuses:**\n"
                "• 🏆 POTD: 15 pts base + bonuses for 2nd/3rd solve\n"
                "• 🔥 Daily Streak: +5 pts (consecutive days)\n"
                "• 📅 Weekly Streak: +20 pts (consecutive weeks)\n"
            ),
            inline=False
        )
        
        # =============== STATS ===============
        embed.add_field(
            name="📊 Stats & Rankings",
            value=(
                "**`/stats`** - View your statistics\n"
                "• Total points, rank, streaks, last submission\n"
                "• Optional: `/stats user:@someone`\n"
                "\n"
                "**`/leaderboard`** - View top performers\n"
                "• **Filters:**\n"
                "  - `period`: Weekly (default), Monthly, All-Time\n"
                "  - `year`: 1st, 2nd, 3rd, 4th Year\n"
                "• Examples:\n"
                "  - `/leaderboard` → Weekly, All Years\n"
                "  - `/leaderboard period:monthly year:2` → Monthly Year 2\n"
                "  - `/leaderboard period:all-time` → Global rankings\n"
                "\n"
                "**Weekly Period:** Monday to Sunday\n"
                "**Monthly Period:** 1st to last day of current month\n"
            ),
            inline=False
        )
        
        # =============== DAILY CHALLENGE ===============
        embed.add_field(
            name="🏆 Daily Challenge (POTD)",
            value=(
                "**`/potd`** - View today's Problem of the Day\n"
                "• Shows active POTD problems for all platforms\n"
                "• Includes direct solve links\n"
                "\n"
                "**POTD Rewards:**\n"
                "• Base: 15 points (fixed)\n"
                "• 2nd POTD solve of the day: +5 bonus\n"
                "• 3rd POTD solve of the day: +10 bonus\n"
            ),
            inline=False
        )
        
        # =============== ADMIN ONLY ===============
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "**`/addproblem`** - Add a problem to database\n"
                "• LeetCode/CF: Verifies via API\n"
                "• GFG: Accepts full URL, auto-extracts slug\n"
                "  - Example: `/addproblem problem_slug:https://www.geeksforgeeks.org/problems/detect-cycle-in-an-undirected-graph/ ...`\n"
                "  - **Note:** All GFG problems forced to Easy (1st Year)\n"
                "\n"
                "**`/setpotd`** - Set today's POTD\n"
                "**`/removepotd`** - Remove POTD status from a problem\n"
                "**`/clearpotd`** - Clear all active POTDs\n"
                "**`/force_potd`** - Manually trigger POTD selection\n"
                "**`/bulkaddproblems`** - Import problems from JSON file\n"
            ),
            inline=False
        )
        
        # =============== QUICK REFERENCE ===============
        embed.add_field(
            name="🎯 Quick Reference",
            value=(
                "**Points System:**\n"
                "• Easy: 10 | Medium: 20 | Hard: 40\n"
                "• POTD: 15 + bonuses\n"
                "• Daily Streak: +5 | Weekly Streak: +20\n"
                "\n"
                "**Rules:**\n"
                "• Submit in #dsa or #potd channels only\n"
                "• One submission per problem (no duplicates)\n"
                "• 10-second cooldown between submissions\n"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="💡 Tip: Start with /setup, then check /potd daily for bonus points!",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    """Load the HelpCog"""
    await bot.add_cog(HelpCog(bot))
