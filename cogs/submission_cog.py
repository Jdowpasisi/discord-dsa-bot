"""
Submission Cog - Handle LeetCode problem submissions with slash commands
Includes channel restrictions, rate limiting, and full validation
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import config
from utils.logic import (
    normalize_problem_name,
    validate_submission,
    calculate_streaks,
    calculate_points,
    format_streak_message,
    validate_difficulty,
    SubmissionStatus
)
from utils.leetcode_api import get_leetcode_api


# Allowed channels for submissions
ALLOWED_CHANNELS = ["dsa", "potd"]


class SubmissionCog(commands.Cog):
    """Cog for handling problem submissions with slash commands"""
    
    def __init__(self, bot):
        self.bot = bot
        print("  → SubmissionCog initialized with /leetcode_submit command")
        
    def check_channel(self, interaction: discord.Interaction) -> bool:
        """
        Check if command is used in an allowed channel
        """
        if not interaction.channel:
            return False
            
        channel_name = interaction.channel.name.lower()
        return channel_name in ALLOWED_CHANNELS
    
    @app_commands.command(
        name="leetcode_submit",
        description="Submit a completed LeetCode problem"
    )
    @app_commands.describe(
        problem_name="LeetCode problem name or slug (e.g., 'two-sum' or 'Two Sum')"
    )
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)  # 1 submission per 30 seconds
    async def leetcode_submit(
        self,
        interaction: discord.Interaction,
        problem_name: str
    ):
        # ============ CHANNEL RESTRICTION CHECK ============
        if not self.check_channel(interaction):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🚫 Wrong Channel",
                    description=(
                        f"The `/leetcode_submit` command can only be used in:\n"
                        f"• <#{interaction.guild.text_channels[0].id}> (if #dsa exists)\n"
                        f"• <#{interaction.guild.text_channels[0].id}> (if #potd exists)\n\n"
                        f"Current channel: #{interaction.channel.name}"
                    ),
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Defer response as database operations might take time
        await interaction.response.defer()
        
        try:
            # ============ STEP 1: NORMALIZE INPUT ============
            discord_id = interaction.user.id
            problem_slug = normalize_problem_name(problem_name)
            
            # ============ STEP 2: CHECK/CREATE USER ============
            user = await self.bot.db.get_user(discord_id)
            if not user:
                await self.bot.db.create_user(discord_id)
                user = await self.bot.db.get_user(discord_id)
            
            # ============ STEP 3: VALIDATE SUBMISSION ============
            # Show "Checking LeetCode..." message
            checking_embed = discord.Embed(
                title="🔍 Checking LeetCode...",
                description=f"Verifying problem: `{problem_slug}`",
                color=config.COLOR_PRIMARY
            )
            await interaction.followup.send(embed=checking_embed)
            
            status, message, problem_data = await validate_submission(
                self.bot.db,
                discord_id,
                problem_slug,
                None  # Difficulty auto-detected from LeetCode API
            )
            
            # ============ HANDLE DUPLICATE SUBMISSION ============
            if status == SubmissionStatus.DUPLICATE:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="⚠️ Already Solved!",
                        description=(
                            f"**Problem:** `{problem_slug}`\n"
                            f"**Status:** You've already submitted this problem.\n\n"
                            f"**Points Awarded:** 0 (no duplicate points)\n\n"
                            f"💡 Try submitting a different problem to keep your streak going!"
                        ),
                        color=config.COLOR_WARNING
                    )
                )
                return
            
            # ============ HANDLE INVALID SUBMISSION ============
            if status == SubmissionStatus.INVALID:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="❌ Invalid Submission",
                        description=message,
                        color=config.COLOR_ERROR
                    )
                )
                return
            
            # ============ VALID SUBMISSION - PROCESS ============
            
            # Extract real problem data from API
            real_difficulty = problem_data["difficulty"]
            real_title = problem_data["title"]
            question_id = problem_data["question_id"]
            
            # Ensure problem exists in database (for tracking purposes)
            problem = await self.bot.db.get_problem(problem_slug)
            if not problem:
                # Auto-create problem with real data from LeetCode
                await self.bot.db.create_problem(
                    problem_slug=problem_slug,
                    difficulty=real_difficulty,
                    topic="General",
                    date_posted=datetime.now().date().isoformat()
                )
            
            # ============ STEP 4: CALCULATE POINTS ============
            base_points = calculate_points(real_difficulty, is_duplicate=False)
            total_points = base_points
            
            # ============ STEP 5: CALCULATE STREAKS ============
            now = datetime.now()
            current_week = now.strftime("%Y-%W")
            
            streak_result = calculate_streaks(user, now)
            daily_streak = streak_result["daily_streak"]
            weekly_streak = streak_result["weekly_streak"]
            streak_maintained = streak_result["streak_maintained"]
            new_week = streak_result["new_week"]
            
            # Apply streak bonuses
            bonus_points = 0
            bonus_messages = []
            
            if not streak_maintained:
                # New submission today (not already submitted)
                if daily_streak > 1:
                    bonus_points += config.DAILY_STREAK_BONUS
                    bonus_messages.append(f"+{config.DAILY_STREAK_BONUS} daily streak bonus")
                
                if new_week and weekly_streak > 1:
                    bonus_points += config.WEEKLY_STREAK_BONUS
                    bonus_messages.append(f"+{config.WEEKLY_STREAK_BONUS} weekly streak bonus")
            
            total_points += bonus_points
            
            # ============ STEP 6: UPDATE DATABASE ============
            
            # Record submission
            submission_date = now.isoformat()
            submission_id = await self.bot.db.create_submission(
                discord_id=discord_id,
                problem_slug=problem_slug,
                submission_date=submission_date,
                points_awarded=total_points
            )
            
            # Update user points
            await self.bot.db.update_user_points(discord_id, total_points)
            
            # Update user streaks
            await self.bot.db.update_user_streaks(
                discord_id=discord_id,
                daily_streak=daily_streak,
                weekly_streak=weekly_streak,
                last_submission_date=submission_date,
                last_week_submitted=current_week
            )
            
            # ============ STEP 7: SEND SUCCESS RESPONSE ============
            
            updated_user = await self.bot.db.get_user(discord_id)
            
            embed = discord.Embed(
                title="✅ Accepted!",
                description=f"Successfully submitted **{real_title}** (#{question_id})",
                color=config.COLOR_SUCCESS
            )
            
            embed.add_field(name="📝 Problem", value=f"[{real_title}](https://leetcode.com/problems/{problem_slug})", inline=True)
            embed.add_field(name="⚡ Difficulty", value=real_difficulty, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            points_text = f"**+{total_points}** points"
            if bonus_points > 0:
                points_text += f"\n({base_points} base + {bonus_points} bonus)"
            
            embed.add_field(name="💰 Points Earned", value=points_text, inline=True)
            embed.add_field(name="🏆 Total Points", value=f"**{updated_user['total_points']}**", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            embed.add_field(name="🔥 Daily Streak", value=f"**{daily_streak}** day{'s' if daily_streak != 1 else ''}", inline=True)
            embed.add_field(name="📅 Weekly Streak", value=f"**{weekly_streak}** week{'s' if weekly_streak != 1 else ''}", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            if bonus_messages:
                embed.add_field(name="🎁 Bonuses Applied", value="\n".join(f"• {msg}" for msg in bonus_messages), inline=False)
            
            if daily_streak >= 7:
                footer_msg = f"🔥 Amazing! {daily_streak}-day streak! Keep it going!"
            elif daily_streak >= 3:
                footer_msg = f"Great progress! {daily_streak} days in a row!"
            else:
                footer_msg = "Keep grinding! 💪"
            
            embed.set_footer(text=footer_msg, icon_url=interaction.user.display_avatar.url)
            embed.timestamp = datetime.now()
            
            # Edit the checking message with success
            await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            print(f"Error in submit command: {e}")
            import traceback
            traceback.print_exc()
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred. Please try again later.",
                color=config.COLOR_ERROR
            )
            
            try:
                if interaction.response.is_done():
                    await interaction.edit_original_response(embed=error_embed)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                pass
    
    @leetcode_submit.error
    async def leetcode_submit_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            retry_after = int(error.retry_after)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⏱️ Cooldown Active",
                    description=f"Please wait **{retry_after}s** before submitting again.",
                    color=config.COLOR_WARNING
                ),
                ephemeral=True
            )
        else:
            print(f"Error in submit command: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=discord.Embed(title="❌ Error", description="An error occurred.", color=config.COLOR_ERROR),
                    ephemeral=True
                )
    
    # ============ LEGACY PREFIX COMMAND SUPPORT ============
    @commands.command(name="submit", aliases=["sub"])
    async def submit_prefix(self, ctx, problem_name: str, difficulty: str = None):
        await ctx.send(
            embed=discord.Embed(
                title="ℹ️ Use Slash Command",
                description=f"Please use `/leetcode_submit problem_name:{problem_name}` instead!",
                color=config.COLOR_INFO
            )
        )


async def setup(bot):
    """
    Load the SubmissionCog using standard registration.
    """
    await bot.add_cog(SubmissionCog(bot))
    print("  ✓ SubmissionCog loaded (Standard Method)")