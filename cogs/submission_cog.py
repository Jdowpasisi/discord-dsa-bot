"""
Submission Cog - POTD vs Non-POTD Evaluation Logic
--------------------------------------------------
Updated based on Internal Design Note:
1. POTD Problems: Fixed 15 pts base + Bonus for 2nd/3rd solve of the day.
2. Non-POTD Problems: Standard Difficulty Scoring (10/20/40).
3. Streaks: Calculated normally.
4. PLATFORM-AWARE: POTD checks now include platform to prevent cross-platform collisions
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
        print("  → SubmissionCog initialized (Platform-Aware POTD Model)")

    def check_channel(self, interaction: discord.Interaction) -> bool:
        if not interaction.channel: return False
        return interaction.channel.name.lower() in ALLOWED_CHANNELS

    @app_commands.command(name="submit", description="Submit a problem from any platform")
    @app_commands.describe(
        problem="Problem Name (LC Slug) or ID (CF 1872A)",
        platform="The platform you solved it on"
    )
    @app_commands.choices(platform=[
        app_commands.Choice(name="LeetCode", value="LeetCode"),
        app_commands.Choice(name="Codeforces", value="Codeforces"),
        app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
    ])
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def submit(
        self,
        interaction: discord.Interaction,
        problem: str,
        platform: app_commands.Choice[str]
    ):
        # 1. Channel check
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
            # 2. Setup
            discord_id = interaction.user.id
            now = datetime.now()
            today_str = now.date().isoformat()
            selected_platform = platform.value

            # 3. Platform-aware normalization
            if selected_platform == "LeetCode":
                normalized_problem = normalize_problem_name(problem)
            else:
                normalized_problem = problem.strip()

            # 4. Ensure user exists
            user = await self.bot.db.get_user(discord_id)
            if not user:
                await self.bot.db.create_user(discord_id)
                user = await self.bot.db.get_user(discord_id)

            # 5. Verify submission
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"🔍 Verifying `{normalized_problem}` on {selected_platform}...",
                    color=config.COLOR_PRIMARY
                )
            )

            status, message, problem_data = await validate_submission(
                self.bot.db,
                discord_id,
                normalized_problem,
                platform=selected_platform,
                current_date=now
            )

            if status != SubmissionStatus.VALID:
                color = config.COLOR_WARNING if status == SubmissionStatus.DUPLICATE else config.COLOR_ERROR
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="Submission Failed",
                        description=message,
                        color=color
                    )
                )
                return

            # 6. Extract problem data
            real_difficulty = problem_data["difficulty"]
            real_title = problem_data["title"]
            problem_slug = problem_data["problem_slug"]

            # Force backend difficulty for GFG - treat all as Easy (10 points)
            if selected_platform == "GeeksforGeeks":
                real_difficulty = "Easy"

            # ✅ CRITICAL FIX: Check if problem exists in DB first, then check POTD status
            existing_problem = await self.bot.db.get_problem(problem_slug, selected_platform)
            
            is_potd = False
            
            if existing_problem:
                # Check 1: Is the 'is_potd' flag set to 1 AND potd_date matches today?
                if existing_problem.get("is_potd") == 1 and existing_problem.get("potd_date") == today_str:
                    is_potd = True
                
                # Check 2 (Fallback): Does the date_posted match today (legacy support)?
                elif existing_problem.get("date_posted") == today_str:
                    is_potd = True
            
            # If problem doesn't exist, create it as NON-POTD (date_posted will be NULL)
            if not existing_problem:
                await self.bot.db.create_problem(
                    problem_slug=problem_slug,
                    platform=selected_platform,
                    problem_title=real_title,
                    difficulty=real_difficulty,
                    academic_year="2",  # Default to year 2 for user-submitted problems
                    topic="General",
                    date_posted=None  # NULL for non-POTD problems
                )

            # 7. Scoring Logic
            base_points = 0
            bonus_points = 0
            bonus_desc = []

            if is_potd:
                base_points = 15
                # Count how many POTD problems user has solved today on this platform
                count = await self.bot.db.get_user_potd_count(
                    discord_id,
                    selected_platform,
                    today_str
                )
                solve_number = count + 1

                if solve_number == 2:
                    bonus_points = 5
                    bonus_desc.append("🎯 Double Trouble! (+5)")
                elif solve_number == 3:
                    bonus_points = 10
                    bonus_desc.append("🔥 Hat Trick! (+10)")

                type_label = "🏆 Problem of the Day"

            elif selected_platform == "GeeksforGeeks":
                base_points = calculate_points("Medium")
                type_label = "📘 Practice Problem"

            else:
                base_points = calculate_points(real_difficulty)
                type_label = f"⚡ {real_difficulty} Problem"


            # 8. Streaks
            current_week = now.strftime("%Y-%W")
            streak_data = calculate_streaks(user, now)

            daily_streak = streak_data["daily_streak"]
            weekly_streak = streak_data["weekly_streak"]

            if not streak_data["streak_maintained"]:
                if daily_streak > 1:
                    bonus_points += config.DAILY_STREAK_BONUS
                    bonus_desc.append(f"⚡ Daily Streak (+{config.DAILY_STREAK_BONUS})")
                if streak_data["new_week"] and weekly_streak > 1:
                    bonus_points += config.WEEKLY_STREAK_BONUS
                    bonus_desc.append(f"📅 Weekly Streak (+{config.WEEKLY_STREAK_BONUS})")

            final_points = base_points + bonus_points

            # 9. Record submission
            await self.bot.db.create_submission(
                discord_id,
                problem_slug,
                now.isoformat(),
                final_points,
                platform=selected_platform,
                verification_status="Verified"
            )

            await self.bot.db.update_user_points(discord_id, final_points)
            await self.bot.db.update_user_streaks(
                discord_id,
                daily_streak,
                weekly_streak,
                now.isoformat(),
                current_week
            )

            # 10. Final response
            updated_user = await self.bot.db.get_user(discord_id)

            embed = discord.Embed(title="✅ Accepted!", color=config.COLOR_SUCCESS)
            embed.add_field(name="Problem", value=real_title, inline=True)
            embed.add_field(name="Platform", value=selected_platform, inline=True)
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
            await interaction.edit_original_response(
                content="❌ An internal error occurred."
            )

async def setup(bot):
    await bot.add_cog(SubmissionCog(bot))