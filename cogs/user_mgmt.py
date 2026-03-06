"""
User Management Cog
Handles user profile setup with year level and platform linking
"""

import io
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from typing import Optional

# Valid year levels
VALID_YEARS = ["1", "2", "3", "4", "General"]

# IST timezone — consistent with the rest of the codebase
IST = timezone(timedelta(hours=5, minutes=30))


class UserManagementCog(commands.Cog):
    """User profile management commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Set up or update your profile (year level and platform handles)")
    @app_commands.describe(
        year="Your current year level",
        leetcode="Your LeetCode username",
        codeforces="Your Codeforces handle",
        geeksforgeeks="Your GeeksforGeeks handle or profile URL"
    )
    @app_commands.choices(
        year=[app_commands.Choice(name=y, value=y) for y in VALID_YEARS]
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        year: Optional[app_commands.Choice[str]] = None,
        leetcode: Optional[str] = None,
        codeforces: Optional[str] = None,
        geeksforgeeks: Optional[str] = None
    ):
        """
        Unified setup command for year level and platform handles.
        Users can update any combination of fields in a single command.
        """
        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Check if at least one argument is provided
        if year is None and leetcode is None and codeforces is None and geeksforgeeks is None:
            await interaction.followup.send(
                "❌ Please provide at least one field to update.\n"
                "**Options:** `year`, `leetcode`, `codeforces`, `geeksforgeeks`"
            )
            return

        try:
            discord_id = interaction.user.id
            db = self.bot.db
            updates = []  # Track what was updated for the response
            errors = []   # Track validation errors

            # Ensure user exists
            user = await db.get_user(discord_id)
            if not user:
                await db.create_user(discord_id)

            # --- Validation ---
            
            # Clean handles
            lc_handle = leetcode.strip() if leetcode else None
            cf_handle = codeforces.strip() if codeforces else None
            gfg_handle = geeksforgeeks.strip() if geeksforgeeks else None

            # LeetCode validation
            if lc_handle:
                if " " in lc_handle:
                    errors.append("LeetCode username cannot contain spaces.")
                else:
                    # Uniqueness check using new helper method
                    if await db.check_handle_exists("leetcode_username", lc_handle, discord_id):
                        errors.append(f"LeetCode `{lc_handle}` is already linked to another user.")

            # Codeforces validation
            if cf_handle:
                if " " in cf_handle:
                    errors.append("Codeforces handle cannot contain spaces.")
                else:
                    # Uniqueness check using new helper method
                    if await db.check_handle_exists("codeforces_handle", cf_handle, discord_id):
                        errors.append(f"Codeforces `{cf_handle}` is already linked to another user.")

            # If there are validation errors, report and exit
            if errors:
                error_text = "\n".join(f"• {e}" for e in errors)
                await interaction.followup.send(
                    f"❌ **Validation Failed:**\n{error_text}"
                )
                return

            # --- Apply Updates ---
            
            # Year update
            if year is not None:
                await db.update_user_profile(discord_id, student_year=year.value)
                updates.append(f"Year → **{year.value}**")

            # LeetCode update
            if lc_handle:
                await db.update_user_profile(discord_id, leetcode_username=lc_handle)
                updates.append(f"LeetCode → `{lc_handle}`")

            # Codeforces update
            if cf_handle:
                await db.update_user_profile(discord_id, codeforces_handle=cf_handle)
                updates.append(f"Codeforces → `{cf_handle}`")

            # GeeksforGeeks update
            if gfg_handle:
                await db.update_user_profile(discord_id, gfg_handle=gfg_handle)
                updates.append(f"GeeksforGeeks → `{gfg_handle}`")

            # --- Response ---
            embed = discord.Embed(
                title="✅ Profile Updated",
                description="\n".join(updates),
                color=discord.Color.green()
            )
            embed.set_footer(text="Use /setup again to update any field")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in /setup: {e}")
            import traceback
            traceback.print_exc()
            # Try followup first, if that fails the interaction is already dead
            try:
                await interaction.followup.send(
                    f"❌ Failed to update profile. Error: {type(e).__name__}\n"
                    f"Details: {str(e)[:200]}"
                )
            except:
                pass  # Interaction already expired

    @app_commands.command(name="reset_user", description="Admin: Delete a user from the database")
    @commands.is_owner()
    async def reset_user(self, interaction: discord.Interaction, user: discord.User):
        # Defer immediately
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Use the new delete_user helper method
            await self.bot.db.delete_user(user.id)
            
            await interaction.followup.send(f"✅ User {user.name} has been reset/wiped from database.")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error resetting user: {e}")

    @app_commands.command(
        name="inactive_members",
        description="Admin: List all server members inactive for a given period"
    )
    @app_commands.describe(period="Inactivity period — members with no submission activity in this window")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="Last 7 Days",                   value="7"),
            app_commands.Choice(name="Last 14 Days",                  value="14"),
            app_commands.Choice(name="Last 30 Days",                  value="30"),
            app_commands.Choice(name="Last 60 Days",                  value="60"),
            app_commands.Choice(name="Last 90 Days",                  value="90"),
            app_commands.Choice(name="All Time (Never Submitted)",    value="0"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def inactive_members(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str]
    ):
        """List every server member who has been inactive for the chosen period."""
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ This command can only be used inside a server.")
                return

            # Fetch all DB users' last activity in one query
            db_users = await self.bot.db.get_all_users_activity()
            db_activity = {u["discord_id"]: u["last_submission_date"] for u in db_users}

            period_days = int(period.value)
            now = datetime.now(IST)

            if period_days > 0:
                cutoff_str = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")
            else:
                cutoff_str = None  # "All Time" — only care about NULL

            inactive = []
            for member in guild.members:
                if member.bot:
                    continue

                last_sub = db_activity.get(member.id)  # None if not in DB

                if period_days == 0:
                    # All Time: inactive = never submitted (no record or NULL date)
                    if last_sub is None:
                        inactive.append(member)
                else:
                    # N days: inactive = no submission since cutoff (or never)
                    if last_sub is None:
                        inactive.append(member)
                    else:
                        # last_sub format: "YYYY-MM-DD HH:MM:SS" — compare date portion
                        if last_sub[:10] < cutoff_str:
                            inactive.append(member)

            # Sort alphabetically by display name for readability
            inactive.sort(key=lambda m: m.display_name.lower())

            count = len(inactive)
            total_humans = sum(1 for m in guild.members if not m.bot)
            generated_at = now.strftime("%Y-%m-%d %H:%M IST")

            # ── Build response ──────────────────────────────────────────────
            if count == 0:
                embed = discord.Embed(
                    title="✅ No Inactive Members",
                    description=(
                        f"All **{total_humans}** non-bot members have activity "
                        f"within the selected period."
                    ),
                    color=discord.Color.green()
                )
                embed.add_field(name="Period", value=period.name, inline=True)
                embed.set_footer(text=f"Generated {generated_at}")
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"😴 Inactive Members — {period.name}",
                description=(
                    f"**{count}** of {total_humans} non-bot server members are inactive.\n"
                    f"{'Full list attached as a text file.' if count > 25 else ''}"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Generated {generated_at}")

            if count <= 25:
                # Short enough to show inline
                lines = []
                for i, m in enumerate(inactive, 1):
                    last = db_activity.get(m.id)
                    last_str = last[:10] if last else "Never"
                    lines.append(f"`{i:2}.` {m.display_name} — last active: **{last_str}**")
                embed.add_field(name="Members", value="\n".join(lines), inline=False)
                await interaction.followup.send(embed=embed)
            else:
                # Build a plain-text file for larger lists
                file_lines = [
                    f"Inactive Members Report",
                    f"Period  : {period.name}",
                    f"Server  : {guild.name}",
                    f"Generated: {generated_at}",
                    f"Inactive: {count} / {total_humans} members",
                    "=" * 60,
                ]
                for i, m in enumerate(inactive, 1):
                    last = db_activity.get(m.id)
                    last_str = last[:10] if last else "Never"
                    file_lines.append(
                        f"{i:4}. {m.display_name:<32} ({m.name:<32}) | Last active: {last_str}"
                    )

                file_content = "\n".join(file_lines).encode("utf-8")
                filename = f"inactive_{'alltime' if period_days == 0 else f'{period_days}days'}.txt"
                await interaction.followup.send(
                    embed=embed,
                    file=discord.File(io.BytesIO(file_content), filename=filename)
                )

        except Exception as e:
            print(f"Error in /inactive_members: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"❌ Failed to fetch inactive members. "
                    f"Error: {type(e).__name__}: {str(e)[:200]}"
                )
            except Exception:
                pass


async def setup(bot: commands.Bot) -> None:
    """Load the UserManagementCog"""
    await bot.add_cog(UserManagementCog(bot))