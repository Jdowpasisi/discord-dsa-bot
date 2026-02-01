"""
User Management Cog
Handles user profile setup with year level and platform linking
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

# Valid year levels
VALID_YEARS = ["1", "2", "3", "4", "General"]


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
            # Try followup first, if that fails the interaction is already dead
            try:
                await interaction.followup.send(
                    "❌ Failed to update profile. Please try again."
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


async def setup(bot: commands.Bot) -> None:
    """Load the UserManagementCog"""
    await bot.add_cog(UserManagementCog(bot))