"""
User Management Cog
Handles user profile setup with year level and LeetCode username
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional


class UserManagementCog(commands.Cog):
    """User profile management commands"""
    
    # Valid year levels
    VALID_YEARS = ["1", "2", "3", "4", "General"]
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="setup", description="Setup your profile with year level and LeetCode username")
    @app_commands.describe(
        year="Your year level (1, 2, 3, 4, or General)",
        leetcode_username="Your LeetCode username (no spaces)"
    )
    @app_commands.choices(year=[
        app_commands.Choice(name="1st Year", value="1"),
        app_commands.Choice(name="2nd Year", value="2"),
        app_commands.Choice(name="3rd Year", value="3"),
        app_commands.Choice(name="4th Year", value="4"),
        app_commands.Choice(name="General/Alumni", value="General")
    ])
    async def setup(
        self,
        interaction: discord.Interaction,
        year: app_commands.Choice[str],
        leetcode_username: str
    ) -> None:
        """
        Setup user profile with year level and LeetCode username.
        """
        try:
            discord_id = interaction.user.id
            selected_year = year.value
            
            # Validate leetcode_username (simple check: no spaces)
            if " " in leetcode_username:
                await interaction.response.send_message(
                    "❌ LeetCode username cannot contain spaces",
                    ephemeral=True
                )
                return
                
            if not leetcode_username.strip():
                await interaction.response.send_message(
                    "❌ LeetCode username cannot be empty",
                    ephemeral=True
                )
                return
                
            # Get database manager from bot context
            db = self.bot.db
            
            # Check if user exists, create if not
            user = await db.get_user(discord_id)
            if not user:
                await db.create_user(discord_id)
            
            # Check if leetcode_username is already taken
            # We access the raw connection via db.db
            async with db.db.execute(
                "SELECT discord_id FROM Users WHERE leetcode_username = ? AND discord_id != ?",
                (leetcode_username, discord_id)
            ) as cursor:
                existing_user = await cursor.fetchone()
                if existing_user:
                    await interaction.response.send_message(
                        f"❌ LeetCode username '{leetcode_username}' is already taken by another user",
                        ephemeral=True
                    )
                    return
            
            # Update user profile
            await db.update_user_profile(
                discord_id,
                student_year=selected_year,
                leetcode_username=leetcode_username
            )
            
            # Send success message
            embed = discord.Embed(
                title="✅ Profile Setup Complete!",
                color=discord.Color.green()
            )
            embed.add_field(name="Year Level", value=year.name, inline=True)
            embed.add_field(name="LeetCode Username", value=leetcode_username, inline=True)
            embed.set_footer(text="You can now start submitting problems!")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in /setup command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="reset_user", description="Admin: Delete a user from the database")
    @commands.is_owner()
    async def reset_user(self, interaction: discord.Interaction, user: discord.User):
        # Defer immediately
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Access the underlying aiosqlite connection (.db.db)
            if not self.bot.db.db:
                await self.bot.db.connect()

            # Execute Deletions
            await self.bot.db.db.execute("DELETE FROM Submissions WHERE discord_id = ?", (user.id,))
            await self.bot.db.db.execute("DELETE FROM Users WHERE discord_id = ?", (user.id,))
            
            # CRITICAL: You must commit changes for deletions to happen
            await self.bot.db.db.commit()
            
            await interaction.followup.send(f"✅ User {user.name} has been reset/wiped from database.")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error resetting user: {e}")

async def setup(bot: commands.Bot) -> None:
    """Load the UserManagementCog"""
    await bot.add_cog(UserManagementCog(bot))