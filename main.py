"""
LeetCode Discord Bot - Main Entry Point
A comprehensive Discord bot for tracking LeetCode problem submissions and maintaining leaderboards

Features:
- Daily automated problem posting with topic rotation
- Submission tracking with points and streaks
- Weekly and monthly leaderboards
- Statistics dashboard
- Comprehensive error handling
- PostgreSQL/Supabase database for scalability

Usage:
    python main.py

Requirements:
    - Python 3.8+
    - discord.py 2.3.0+
    - asyncpg 0.29.0+
    - python-dotenv 1.0.0+
    - aiohttp 3.8.0+ (for LeetCode API)

Environment Variables:
    DISCORD_TOKEN - Your Discord bot token (required)
    DATABASE_URL - PostgreSQL connection URL from Supabase (required)
"""

from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Import configuration and database manager
import config
from database import DatabaseManager
from utils.leetcode_api import close_leetcode_api

print("📦 Using PostgreSQL/Supabase database")


class LeetCodeBot(commands.Bot):
    """Custom Bot class with database integration and comprehensive error handling"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=config.COMMAND_PREFIX,
            description=config.BOT_DESCRIPTION,
            intents=intents
        )
        
        # Initialize PostgreSQL database manager
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.db = DatabaseManager(config.DATABASE_URL)
        self.start_time = datetime.now()
    
    async def is_owner(self, user: discord.User) -> bool:
        """Check if user is the bot owner"""
        if self.owner_id:
            return user.id == self.owner_id
        # Fetch owner if not cached
        app = await self.application_info()
        self.owner_id = app.owner.id
        return user.id == self.owner_id
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        print(f"\n{'='*60}")
        print(f"🚀 LeetCode Discord Bot - Initialization")
        print(f"{'='*60}")
        
        # Connect to database
        print("📊 Connecting to database...")
        await self.db.connect()
        await self.db.initialize_tables()
        
        # Load cogs
        print("\n🔌 Loading cogs...")
        await self.load_cogs()
        
        # =========================================================================
        # UPDATED SYNC COMMAND - THE FIX IS HERE
        # =========================================================================
        @self.command(name='sync', hidden=True)
        async def sync_commands(ctx: commands.Context, scope: str = "guild"):
            """
            Owner-only sync.
            Usage: !sync (Syncs global commands to THIS server instantly)
            """
            if not await self.is_owner(ctx.author):
                return  # Silently ignore non-owners
            
            # Delete the command message to reduce clutter
            try:
                await ctx.message.delete()
            except:
                pass
            
            try:
                # 1. GLOBAL SYNC (Slow, takes 1 hour to update)
                if scope.lower() == "global":
                    msg = await ctx.send("⏳ Syncing **globally** (updates in ~1 hour)...")
                    synced = await self.tree.sync()
                    await msg.edit(content=f"✅ Synced {len(synced)} global commands.", delete_after=3)
                    print(f"Global sync: {len(synced)} commands")
                    
                # 2. GUILD SYNC (The "Copy" Trick - Instant Update)
                else:
                    if not ctx.guild:
                        await ctx.send("❌ Guild sync must be run inside a server.", delete_after=3)
                        return

                    msg = await ctx.send(f"⏳ Syncing commands to **{ctx.guild.name}**...")
                    
                    # STEP A: Clear old guild commands
                    self.tree.clear_commands(guild=ctx.guild)
                    
                    # STEP B: Copy GLOBAL commands (from cogs) to THIS GUILD
                    # This makes global commands appear instantly in this server
                    self.tree.copy_global_to(guild=ctx.guild)
                    
                    # STEP C: Sync
                    synced = await self.tree.sync(guild=ctx.guild)
                    
                    await msg.edit(
                        content=f"✅ Synced {len(synced)} commands: {', '.join(f'`/{cmd.name}`' for cmd in synced)}",
                        delete_after=3
                    )
                    print(f"Guild sync ({ctx.guild.name}): {len(synced)} commands")
                
            except Exception as e:
                await ctx.send(f"❌ Sync failed: {e}", delete_after=3)
                print(f"Sync error: {e}")

        # Register error handler
        self.tree.error(self.on_app_command_error)
        print("✓ Setup complete\n")


    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        # Explicitly list cogs to load (prevents loading deprecated/old versions)
        cogs_to_load = [
            "submission_cog",  # NEW: Slash command version with LeetCode API
            "scheduler_cog",
            "stats_cog",
            "help_cog",
            "leaderboard",
            "problems",
            "user_mgmt"  # User profile setup with year and LeetCode username
        ]
        
        loaded = 0
        failed = 0
        
        print(f"  Loading {len(cogs_to_load)} cog(s)...\n")
        
        for cog_name in cogs_to_load:
            cog_path = f"cogs.{cog_name}"
            try:
                await self.load_extension(cog_path)
                print(f"  ✓ {cog_name.ljust(20)} - Loaded successfully")
                loaded += 1
            except Exception as e:
                print(f"  ✗ {cog_name.ljust(20)} - Failed: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        print(f"\n  Summary: {loaded} loaded, {failed} failed")
        
        if failed > 0:
            print(f"  ⚠️  WARNING: {failed} cog(s) failed to load - check errors above")
                
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        print(f"\n{'='*60}")
        print(f"✅ Bot is now ONLINE and ready!")
        print(f"{'='*60}")
        print(f"👤 Logged in as: {self.user.name} (ID: {self.user.id})")
        print(f"🌐 Connected to {len(self.guilds)} guild(s):")
        
        for guild in self.guilds:
            print(f"   • {guild.name} (ID: {guild.id}) - {guild.member_count} members")
        
        print(f"\n⌨️  Command prefix: {config.COMMAND_PREFIX}")
        
        # DEBUG: Check command tree state
        all_commands = self.tree.get_commands()
        print(f"\n🔍 DEBUG: Commands registered in tree: {[cmd.name for cmd in all_commands]}")
        print(f"   Total commands: {len(all_commands)}")
        
        if len(all_commands) == 0:
            print("\n⚠️  WARNING: Command tree is EMPTY!")
            print("   This means cogs loaded but commands weren't registered to tree.")
            print("   Check cog setup() functions for bot.tree.add_command() calls")
        
        # Sync slash commands
        print("\n🔄 Syncing slash commands with Discord...")
        try:
            synced = await self.tree.sync()
            print(f"✓ Successfully synced {len(synced)} slash command(s):")
            for cmd in synced:
                print(f"   • /{cmd.name}")
        except Exception as e:
            print(f"✗ Failed to sync commands: {e}")
        
        # Calculate uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        print(f"\n⚡ Bot ready in {uptime:.2f} seconds")
        print(f"{'='*60}\n")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"/bot_info | Daily LeetCode Problems"
            )
        )
        
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global error handler for prefix commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
            
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Missing Argument",
                    description=f"Missing required argument: `{error.param.name}`\n"
                               f"Use `{config.COMMAND_PREFIX}help {ctx.command}` for more info.",
                    color=config.COLOR_ERROR
                )
            )
            
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Missing Permissions",
                    description="You don't have permission to use this command.",
                    color=config.COLOR_ERROR
                )
            )
            
        else:
            # Log unexpected errors
            print(f"Error in command {ctx.command}: {error}")
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="An unexpected error occurred.",
                    color=config.COLOR_ERROR
                )
            )
    
    async def on_app_command_error(
        self, 
        interaction: discord.Interaction, 
        error: discord.app_commands.AppCommandError
    ):
        """Global error handler for slash commands - ensures bot never crashes"""
        
        # Handle rate limiting (cooldown)
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⏱️ Cooldown Active",
                    description=f"Please wait **{error.retry_after:.1f} seconds** before using this command again.",
                    color=config.COLOR_WARNING
                ),
                ephemeral=True
            )
            return
        
        # Handle missing permissions
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Missing Permissions",
                    description="You don't have permission to use this command.",
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Handle bot missing permissions
        if isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bot Missing Permissions",
                    description="I don't have the required permissions to execute this command.",
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Handle command not found
        if isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❓ Command Not Found",
                    description="This command doesn't exist. Use `/bot_info` to see available commands.",
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Handle transformation errors (invalid input types)
        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Invalid Input",
                    description=f"Invalid input provided: {str(error)}\n\n"
                               "Please check your command parameters and try again.",
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Handle check failures (channel restrictions, etc.)
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🚫 Check Failed",
                    description="You cannot use this command here or now.",
                    color=config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        # Log all other errors and send generic message
        print(f"\n{'='*50}")
        print(f"❌ Unhandled Slash Command Error")
        print(f"Command: {interaction.command.name if interaction.command else 'Unknown'}")
        print(f"User: {interaction.user} (ID: {interaction.user.id})")
        print(f"Guild: {interaction.guild.name if interaction.guild else 'DM'}")
        print(f"Error Type: {type(error).__name__}")
        print(f"Error: {error}")
        print(f"{'='*50}\n")
        
        # Send user-friendly error message
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Unexpected Error",
                        description="An unexpected error occurred while processing your command.\n"
                                   "The error has been logged. Please try again later.",
                        color=config.COLOR_ERROR
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Unexpected Error",
                        description="An unexpected error occurred while processing your command.\n"
                                   "The error has been logged. Please try again later.",
                        color=config.COLOR_ERROR
                    ),
                    ephemeral=True
                )
        except Exception as send_error:
            print(f"Failed to send error message: {send_error}")
            
    async def close(self):
        """Cleanup when bot is shutting down"""
        print("\n🔄 Shutting down bot...")
        print("  • Closing database connection...")
        await self.db.close()
        print("  • Closing LeetCode API session...")
        await close_leetcode_api()
        print("  • Closing Discord connection...")
        await super().close()
        print("✓ Cleanup complete")


async def main():
    """Main function to run the bot with comprehensive error handling"""
    
    # Print banner
    print("\n" + "="*60)
    print(" "*15 + "🤖 LeetCode Discord Bot")
    print(" "*20 + "v1.0.0")
    print("="*60 + "\n")
    
    # Check if token is set
    if not config.DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in environment variables")
        print("\n📋 Setup Instructions:")
        print("1. Create a .env file in the project root")
        print("2. Add your Discord bot token:")
        print("   DISCORD_TOKEN=your_token_here")
        print("\n💡 Get your token from: https://discord.com/developers/applications")
        sys.exit(1)
    
    # Verify required directories exist
    print("📁 Verifying directory structure...")
    required_dirs = ["data", "cogs", "database", "utils"]
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"   ✓ {dir_name}/ exists")
        else:
            print(f"   ⚠️  {dir_name}/ not found - creating...")
            dir_path.mkdir(exist_ok=True)
    
    # Verify problem bank exists
    problem_bank_path = Path("data/problem_bank.json")
    if problem_bank_path.exists():
        print(f"   ✓ data/problem_bank.json exists")
    else:
        print(f"   ⚠️  data/problem_bank.json not found")
        print("      SchedulerCog may not function correctly")
    
    print("\n🤖 Initializing bot...\n")
    
    # Start web server FIRST so Render marks service as "Live"
    # This prevents deployment from hanging if database connection is slow
    keep_alive()
    print("🌍 Web server started for Render keep-alive")
    print("   Render should now mark this service as Live\n")

    bot = LeetCodeBot()
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received - shutting down bot...")
        await bot.close()
        print("✓ Bot shutdown complete")
    except discord.LoginFailure:
        print("\n❌ ERROR: Invalid Discord token")
        print("Please check your DISCORD_TOKEN in .env file")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        print("\n❌ ERROR: Missing required intents")
        print("\n📋 Fix:")
        print("1. Go to https://discord.com/developers/applications")
        print("2. Select your bot application")
        print("3. Go to 'Bot' section")
        print("4. Enable these Privileged Gateway Intents:")
        print("   - MESSAGE CONTENT INTENT")
        print("   - SERVER MEMBERS INTENT")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {type(e).__name__}")
        print(f"   {e}")
        print("\n📋 Troubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Verify bot permissions in Discord Developer Portal")
        print("3. Ensure all required dependencies are installed")
        print("4. Check the error message above for specific details")
        await bot.close()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Bot stopped")
