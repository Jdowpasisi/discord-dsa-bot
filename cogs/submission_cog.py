"""
Submission Cog - POTD vs Non-POTD Evaluation Logic
--------------------------------------------------
Updated based on Internal Design Note:
1. POTD Problems: Fixed 15 pts base + Bonus for 2nd/3rd solve of the day.
2. Non-POTD Problems: Standard Difficulty Scoring (10/20/40).
3. Streaks: Calculated normally.
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
    SubmissionStatus
)

# Allowed channels for submissions
ALLOWED_CHANNELS = ["dsa", "potd"]

class SubmissionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("  → SubmissionCog initialized (New Scoring Model)")

    def check_channel(self, interaction: discord.Interaction) -> bool:
        if not interaction.channel: return False
        return interaction.channel.name.lower() in ALLOWED_CHANNELS

    @app_commands.command(name="leetcode_submit", description="Submit a completed LeetCode problem")
    @app_commands.describe(problem_name="LeetCode problem name or slug")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def leetcode_submit(self, interaction: discord.Interaction, problem_name: str):
        
        # 1. Channel Check
        if not self.check_channel(interaction):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🚫 Wrong Channel", 
                    description="Please use #dsa or #potd.", 
                    color=config.COLOR_ERROR
                ), 
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # 2. Setup Data
            discord_id = interaction.user.id
            problem_slug = normalize_problem_name(problem_name)
            today_str = datetime.now().date().isoformat()
            now = datetime.now()

            # 3. Ensure User Exists
            user = await self.bot.db.get_user(discord_id)
            if not user:
                await self.bot.db.create_user(discord_id)
                user = await self.bot.db.get_user(discord_id)

            # 4. Verify Submission (API Check)
            await interaction.followup.send(
                embed=discord.Embed(description=f"🔍 Verifying `{problem_slug}`...", color=config.COLOR_PRIMARY)
            )

            status, message, problem_data = await validate_submission(
                self.bot.db, discord_id, problem_slug, current_date=now
            )

            if status != SubmissionStatus.VALID:
                color = config.COLOR_WARNING if status == SubmissionStatus.DUPLICATE else config.COLOR_ERROR
                await interaction.edit_original_response(
                    embed=discord.Embed(title="Submission Failed", description=message, color=color)
                )
                return

            # ==================================================================
            # 5. NEW SCORING LOGIC (The Core Change)
            # ==================================================================
            
            real_difficulty = problem_data["difficulty"]
            real_title = problem_data["title"]
            
            # Check if this is today's POTD
            is_potd = await self.bot.db.is_problem_potd(problem_slug, today_str)
            
            base_points = 0
            bonus_points = 0
            bonus_desc = []
            
            if is_potd:
                # --- POTD SCORING ---
                base_points = 15  # Fixed base for POTD
                
                # Check how many POTDs user has ALREADY solved today
                count_before_this = await self.bot.db.get_user_potd_count(discord_id, today_str)
                solve_number = count_before_this + 1
                
                if solve_number == 2:
                    bonus_points = 5
                    bonus_desc.append("🎯 Double Trouble! (+5)")
                elif solve_number == 3:
                    bonus_points = 10
                    bonus_desc.append("🔥 Hat Trick! (+10)")
                    
                type_label = "🏆 Problem of the Day"
            else:
                # --- NON-POTD SCORING ---
                base_points = calculate_points(real_difficulty)
                type_label = f"⚡ {real_difficulty} Problem"

            # ==================================================================

            # 6. Streak Calculation
            current_week = now.strftime("%Y-%W")
            streak_data = calculate_streaks(user, now)
            
            daily_streak = streak_data["daily_streak"]
            weekly_streak = streak_data["weekly_streak"]
            
            # Apply Streak Bonuses (if not maintained/already awarded today)
            if not streak_data["streak_maintained"]:
                if daily_streak > 1:
                    bonus_points += config.DAILY_STREAK_BONUS
                    bonus_desc.append(f"⚡ Daily Streak (+{config.DAILY_STREAK_BONUS})")
                if streak_data["new_week"] and weekly_streak > 1:
                    bonus_points += config.WEEKLY_STREAK_BONUS
                    bonus_desc.append(f"📅 Weekly Streak (+{config.WEEKLY_STREAK_BONUS})")

            final_points = base_points + bonus_points

            # 7. Update Database
            # Ensure problem exists in DB (for tracking)
            if not await self.bot.db.get_problem(problem_slug):
                await self.bot.db.create_problem(
                    problem_slug=problem_slug,
                    problem_title=real_title,     # <--- Added Title
                    difficulty=real_difficulty,   # <--- Corrected mapping
                    topic="General",
                    date_posted=today_str         # <--- Explicitly passed to correct arg
                )

            await self.bot.db.create_submission(discord_id, problem_slug, now.isoformat(), final_points)
            await self.bot.db.update_user_points(discord_id, final_points)
            await self.bot.db.update_user_streaks(discord_id, daily_streak, weekly_streak, now.isoformat(), current_week)

            # 8. Final Response
            updated_user = await self.bot.db.get_user(discord_id)
            
            embed = discord.Embed(title="✅ Accepted!", color=config.COLOR_SUCCESS)
            embed.add_field(name="Problem", value=f"[{real_title}](https://leetcode.com/problems/{problem_slug})", inline=True)
            embed.add_field(name="Type", value=type_label, inline=True)
            
            pts_display = f"**+{final_points}**"
            if bonus_points > 0:
                pts_display += f" ({base_points} + {bonus_points} bonus)"
            
            embed.add_field(name="Points", value=pts_display, inline=True)
            embed.add_field(name="Total Score", value=f"**{updated_user['total_points']}**", inline=True)
            
            if bonus_desc:
                embed.add_field(name="🎉 Bonuses", value="\n".join(bonus_desc), inline=False)
                
            embed.set_footer(text=f"Streak: {daily_streak} Days | {weekly_streak} Weeks")
            
            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            print(f"Error in submit: {e}")
            import traceback
            traceback.print_exc()
            await interaction.edit_original_response(content="❌ An internal error occurred.")

async def setup(bot):
    await bot.add_cog(SubmissionCog(bot))