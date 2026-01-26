"""
User Management Cog
Handles user profile setup with year level and LeetCode username
"""

import discord
from discord.ext import commands
from discord import app_commands

# Valid year levels
VALID_YEARS = ["1", "2", "3", "4", "General"]

class UserManagementCog(commands.Cog):
    """User profile management commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="setup", description="Update your year level")
    @app_commands.describe(year="Your current year level")
    @app_commands.choices(
        year=[app_commands.Choice(name=y, value=y) for y in VALID_YEARS]
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        year: app_commands.Choice[str]
    ):
        try:
            discord_id = interaction.user.id
            selected_year = year.value

            user = await self.bot.db.get_user(discord_id)
            if not user:
                await self.bot.db.create_user(discord_id)

            await self.bot.db.update_user_profile(
                discord_id,
                student_year=selected_year
            )

            embed = discord.Embed(
                title="✅ Profile Updated",
                color=discord.Color.green()
            )
            embed.add_field(name="Year Level", value=selected_year, inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in /setup: {e}")
            await interaction.response.send_message(
                "❌ Failed to update profile.",
                ephemeral=True
            )
    @app_commands.command(name="link", description="Link your coding platform profile")
    @app_commands.describe(
        platform="The platform to link",
        handle="Your username/handle"
    )
    @app_commands.choices(platform=[
        app_commands.Choice(name="LeetCode", value="LeetCode"),
        app_commands.Choice(name="Codeforces", value="Codeforces"),
        app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
    ])
    async def link(
        self,
        interaction: discord.Interaction,
        platform: app_commands.Choice[str],
        handle: str
    ):
        try:
            discord_id = interaction.user.id
            selected_platform = platform.value
            clean_handle = handle.strip()

            if not clean_handle:
                await interaction.response.send_message(
                    "❌ Handle cannot be empty.",
                    ephemeral=True
                )
                return

            if " " in clean_handle and selected_platform != "GeeksforGeeks":
                await interaction.response.send_message(
                    "❌ Handle cannot contain spaces.",
                    ephemeral=True
                )
                return

            db = self.bot.db

            user = await db.get_user(discord_id)
            if not user:
                await db.create_user(discord_id)

            # Platform-specific uniqueness checks
            column_map = {
                "LeetCode": "leetcode_username",
                "Codeforces": "codeforces_handle"
            }

            if selected_platform in column_map:
                column = column_map[selected_platform]
                query = f"""
                    SELECT discord_id FROM Users
                    WHERE {column} = ? AND discord_id != ?
                """
                async with db.db.execute(query, (clean_handle, discord_id)) as cursor:
                    if await cursor.fetchone():
                        await interaction.response.send_message(
                            f"❌ `{clean_handle}` is already linked on {selected_platform}.",
                            ephemeral=True
                        )
                        return

            # Update profile
            if selected_platform == "LeetCode":
                await db.update_user_profile(discord_id, leetcode_username=clean_handle)
            elif selected_platform == "Codeforces":
                await db.update_user_profile(discord_id, codeforces_handle=clean_handle)
            else:
                await db.update_user_profile(discord_id, gfg_handle=clean_handle)

            embed = discord.Embed(
                title="🔗 Profile Linked",
                color=discord.Color.green()
            )
            embed.add_field(name="Platform", value=selected_platform, inline=True)
            embed.add_field(name="Username", value=clean_handle, inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in /link: {e}")
            await interaction.response.send_message(
                "❌ Failed to link profile.",
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