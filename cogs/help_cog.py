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
        description="View all available commands"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Display help for general user commands"""
        embed = discord.Embed(
            title="📚 DSA Bot Commands",
            description="Your daily coding companion!",
            color=config.COLOR_PRIMARY
        )
        
        embed.add_field(
            name="👤 /setup — Set up your profile",
            value=(
                "```\n"
                "/setup [year] [leetcode] [codeforces] [geeksforgeeks]\n"
                "```\n"
                "**Examples:**\n"
                "• `/setup year:2` — Set year only\n"
                "• `/setup leetcode:john_doe` — Link LeetCode\n"
                "• `/setup year:3 codeforces:tourist` — Multiple at once"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 /submit — Submit a solved problem",
            value=(
                "```\n"
                "/submit <problem> <platform>\n"
                "```\n"
                "**Examples:**\n"
                "• `/submit problem:two-sum platform:LeetCode`\n"
                "• `/submit problem:1872A platform:Codeforces`\n"
                "• `/submit problem:detect-cycle platform:GeeksforGeeks`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 /potd — View today's Problem of the Day",
            value=(
                "```\n"
                "/potd\n"
                "```\n"
                "Shows all active POTD problems with solve links.\n"
                "POTD submissions earn **15 bonus points**!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 /stats — View user statistics",
            value=(
                "```\n"
                "/stats [user]\n"
                "```\n"
                "**Examples:**\n"
                "• `/stats` — Your own stats\n"
                "• `/stats user:@someone` — View another user"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏅 /leaderboard — View rankings",
            value=(
                "```\n"
                "/leaderboard [limit] [period] [year]\n"
                "```\n"
                "**Examples:**\n"
                "• `/leaderboard` — Weekly, all years (default)\n"
                "• `/leaderboard period:monthly year:2`\n"
                "• `/leaderboard limit:20 period:all-time`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Points System",
            value="Easy: 5 │ Medium: 10 │ Hard: 15 │ POTD: 15",
            inline=False
        )
        
        embed.set_footer(text="Start with /setup │ Admins: use /adminhelp")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="adminhelp",
        description="View admin-only commands"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_help_command(self, interaction: discord.Interaction):
        """Display help for admin commands (ephemeral)"""
        embed = discord.Embed(
            title="⚙️ Admin Commands",
            description="Manage problems and users (all responses are private)",
            color=config.COLOR_WARNING
        )
        
        embed.add_field(
            name="📋 /setpotd — Set Problem of the Day",
            value=(
                "```\n"
                "/setpotd <problem_slug> <platform> <year>\n"
                "```\n"
                "**Examples:**\n"
                "• `/setpotd problem_slug:two-sum platform:LeetCode year:1`\n"
                "• `/setpotd problem_slug:1872A platform:Codeforces year:2`\n"
                "• `/setpotd problem_slug:https://geeksforgeeks.org/problems/detect-cycle/ platform:GeeksforGeeks year:1`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🗑️ /removepotd — Remove POTD status",
            value=(
                "```\n"
                "/removepotd <problem_slug> <platform>\n"
                "```\n"
                "**Example:** `/removepotd problem_slug:two-sum platform:LeetCode`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧹 /clearpotd — Clear all POTDs",
            value=(
                "```\n"
                "/clearpotd\n"
                "```\n"
                "Removes POTD status from ALL active problems."
            ),
            inline=False
        )
        
        embed.add_field(
            name="📦 /problembank — View queue status",
            value=(
                "```\n"
                "/problembank\n"
                "```\n"
                "Shows problem counts per year and upcoming problems."
            ),
            inline=False
        )
        
        embed.add_field(
            name="📥 /bulkaddproblems — Import from JSON",
            value=(
                "```\n"
                "/bulkaddproblems <file>\n"
                "```\n"
                "Upload a JSON file with problem data to bulk import."
            ),
            inline=False
        )
        
        embed.add_field(
            name="👤 /reset_user — Delete user data",
            value=(
                "```\n"
                "/reset_user <user>\n"
                "```\n"
                "**Example:** `/reset_user user:@someone`\n"
                "⚠️ Permanently deletes all user data & submissions."
            ),
            inline=False
        )

        embed.add_field(
            name="😴 /inactive_members — List inactive members",
            value=(
                "```\n"
                "/inactive_members <period>\n"
                "```\n"
                "**Periods:** Last 7 / 14 / 30 / 60 / 90 Days, or All Time (never submitted)\n"
                "Lists **all server members** (including those without a linked account) "
                "who have no submission activity in the chosen period. "
                "Results over 25 members are sent as an attached text file."
            ),
            inline=False
        )

        embed.add_field(
            name="🔧 !sync — Sync slash commands (Owner)",
            value=(
                "```\n"
                "!sync [scope]\n"
                "```\n"
                "• `!sync` — Instant sync to current server\n"
                "• `!sync global` — Global sync (~1 hour delay)"
            ),
            inline=False
        )
        
        embed.set_footer(text="All responses auto-delete or are ephemeral")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the HelpCog"""
    await bot.add_cog(HelpCog(bot))
