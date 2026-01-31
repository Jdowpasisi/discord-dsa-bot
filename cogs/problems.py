"""
Problems Cog - Manage and display problems from multiple platforms
PLATFORM-AWARE: All problem operations now include platform context
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import config
import json
from utils.logic import (
    normalize_problem_name,
    parse_gfg_slug,
    generate_gfg_title,
    generate_problem_url
)
from utils.leetcode_api import get_leetcode_api
from utils.codeforces_api import get_codeforces_api

class Problems(commands.Cog):
    """Commands for managing and viewing problems"""
    
    def __init__(self, bot):
        self.bot = bot
        

    async def _fetch_and_verify_metadata(self, slug: str, platform: str):
        """Helper to fetch metadata from respective APIs"""
        if platform == "LeetCode":
            clean_slug = normalize_problem_name(slug)
            api = get_leetcode_api()
            meta = await api.get_problem_metadata(clean_slug)
            if meta:
                return {
                    "slug": meta.title_slug,
                    "title": meta.title,
                    "difficulty": meta.difficulty 
                }
        
        elif platform == "Codeforces":
            clean_slug = slug.strip().upper() 
            api = get_codeforces_api()
            meta = await api.get_problem_metadata(clean_slug)
            if meta:
                return {
                    "slug": meta["slug"], 
                    "title": meta["title"],
                    "difficulty": meta["difficulty"]
                }
        
        elif platform == "GeeksforGeeks":
            # Use centralized GFG parsing from utils.logic
            clean_slug = parse_gfg_slug(slug)
            clean_title = generate_gfg_title(clean_slug)
            canonical_url = generate_problem_url(platform, clean_slug)
            return {
                "slug": clean_slug,
                "title": canonical_url,  # Store URL as title (Backend Requirement)
                "clean_title": clean_title,  # For display
                "difficulty": "Easy"  # Force Easy
            }
            
        return None
    # ==================================================================
    # 2. Bulk Add Problems
    # ==================================================================
    @app_commands.command(name="bulkaddproblems", description="Add multiple problems from JSON file (Admin only)")
    @app_commands.describe(file="JSON file with problems array")
    @app_commands.checks.has_permissions(administrator=True)
    async def bulk_add_problems(self, interaction: discord.Interaction, file: discord.Attachment):
        """Add multiple problems from a JSON file"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            content = await file.read()
            data = json.loads(content.decode('utf-8'))
            
            if "problems" not in data:
                await interaction.followup.send("❌ JSON must contain a 'problems' array")
                return
            
            problems = data["problems"]
            added, skipped, errors = 0, 0, []
            
            for p in problems:
                try:
                    slug = p["slug"]
                    platform = p.get("platform", "LeetCode")
                    difficulty = p.get("difficulty", "Medium")
                    academic_year = p.get("year", p.get("academic_year", "2"))
                    topic = p.get("topic", "General")
                    
                    # Unified parsing logic using centralized functions
                    if platform == "GeeksforGeeks":
                        clean_slug = parse_gfg_slug(slug)
                        slug = clean_slug
                        title = generate_problem_url(platform, clean_slug)  # Store URL
                        difficulty = "Easy"
                    elif platform == "LeetCode":
                        slug = normalize_problem_name(slug)
                        title = p.get("title", slug)
                    elif platform == "Codeforces":
                        slug = slug.strip().upper()
                        title = p.get("title", slug)
                    else:
                        title = p.get("title", slug)
                    
                    existing = await self.bot.db.get_problem(slug, platform)
                    if existing:
                        skipped += 1
                        continue
                    
                    # Note: We skip API verification for bulk add speed, 
                    # assuming the JSON is prepared correctly.
                    
                    await self.bot.db.create_problem(
                        problem_slug=slug,
                        platform=platform,
                        problem_title=title,
                        difficulty=difficulty,
                        academic_year=academic_year,
                        topic=topic,
                        is_potd=0,
                        potd_date=None
                    )
                    added += 1
                except Exception as e:
                    errors.append(f"{p.get('slug', 'unknown')}: {str(e)}")
            
            embed = discord.Embed(title="📦 Bulk Add Complete", color=config.COLOR_SUCCESS)
            embed.add_field(name="✅ Added", value=str(added), inline=True)
            embed.add_field(name="⏭️ Skipped", value=str(skipped), inline=True)
            embed.add_field(name="❌ Errors", value=str(len(errors)), inline=True)
            
            if errors:
                error_text = "\n".join(errors[:5])
                if len(errors) > 5: error_text += f"\n... and {len(errors) - 5} more"
                embed.add_field(name="Error Details", value=f"```{error_text}```", inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

    # ==================================================================
    # 4. Get Today's POTD
    # ==================================================================
    @app_commands.command(name="potd", description="Get today's POTD (if set)")
    async def daily_problem(self, interaction: discord.Interaction):
        """Get today's problem"""
        await interaction.response.defer()
        
        try:
            today_str = datetime.now().date().isoformat()
            potd_problems = []
            
            for platform in ["LeetCode", "Codeforces", "GeeksforGeeks"]:
                rows = await self.bot.db.get_potd_for_date(today_str, platform)
                potd_problems.extend(rows)
            
            if not potd_problems:
                await interaction.followup.send("🌟 No POTD set for today. Check back later!")
                return
            
            embed = discord.Embed(
                title="🏆 Today's Problem of the Day",
                description=f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
                color=config.COLOR_PRIMARY,
                timestamp=datetime.now()
            )
            
            for problem in potd_problems:
                platform = problem['platform']
                
                if platform == "GeeksforGeeks":
                    # Use centralized GFG parsing
                    clean_slug = parse_gfg_slug(problem['problem_title'])  # title is URL
                    display_title = generate_gfg_title(clean_slug)
                    url = problem['problem_title']
                    # GFG Style: Clean Title, No Difficulty displayed
                    field_name = f"Year {problem.get('academic_year', '?')} : {platform}"
                else:
                    display_title = problem['problem_title']
                    url = generate_problem_url(platform, problem['problem_slug'])
                    # Standard Style
                    field_name = f"Year {problem.get('academic_year', '?')} ({problem['difficulty']}) : {platform}"
                
                embed.add_field(
                    name=field_name,
                    value=f"**{display_title}**\n[Solve Here]({url})",
                    inline=False
                )
            
            embed.set_footer(text="Submit with /submit to earn points!")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error in potd: {e}")
            await interaction.followup.send("❌ Failed to retrieve daily problems.")

    # ==================================================================
    # 5. Set POTD (Manual)
    # ==================================================================
    @app_commands.command(name="setpotd", description="Set Problem of the Day (Admin only)")
    @app_commands.describe(
        problem_slug="Problem slug/ID",
        platform="Platform",
        year="Year Level"
    )
    @app_commands.choices(
        platform=[
            app_commands.Choice(name="LeetCode", value="LeetCode"),
            app_commands.Choice(name="Codeforces", value="Codeforces"),
            app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
        ],
        year=[
            app_commands.Choice(name="1st Year", value="1"),
            app_commands.Choice(name="2nd Year", value="2"),
            app_commands.Choice(name="3rd Year", value="3")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_potd(
        self,
        interaction: discord.Interaction,
        problem_slug: str,
        platform: str,
        year: str
    ):
        """Set a problem as today's POTD with specific Year level"""
        await interaction.response.defer(ephemeral=True)

        # 1. Verify format via API helper (NOW HANDLES GFG URL PARSING)
        meta = await self._fetch_and_verify_metadata(problem_slug, platform)
        if not meta:
            await interaction.followup.send(f"❌ Error: Problem `{problem_slug}` not found on {platform}.")
            return
            
        final_slug = meta["slug"]
        final_title = meta["title"] # URL for GFG, Title for others
        final_difficulty = meta.get("difficulty", "Medium") # Easy for GFG
        
        today = datetime.now().date().isoformat()

        # 2. Upsert (Create or Update)
        await self.bot.db.create_problem(
            problem_slug=final_slug,
            platform=platform,
            problem_title=final_title,
            difficulty=final_difficulty,
            academic_year=year,    # ✅ Updates the year
            topic=None,         
            is_potd=1,          # ✅ Set as POTD
            potd_date=today
        )

        display_name = meta.get("clean_title", final_slug) # Pretty name for message

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ POTD Set",
                description=f"🏆 `{display_name}` is now **Year {year}** POTD on {platform}!",
                color=config.COLOR_SUCCESS
            )
        )
    # ==================================================================
    # 6. Remove POTD
    # ==================================================================
    @app_commands.command(name="removepotd", description="Remove POTD status (Admin only)")
    @app_commands.describe(problem_slug="Problem slug/ID", platform="Platform")
    @app_commands.choices(platform=[
        app_commands.Choice(name="LeetCode", value="LeetCode"),
        app_commands.Choice(name="Codeforces", value="Codeforces"),
        app_commands.Choice(name="GeeksforGeeks", value="GeeksforGeeks")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_potd(self, interaction: discord.Interaction, problem_slug: str, platform: str):
        await interaction.response.defer(ephemeral=True)
        
        # Verify slug format
        meta = await self._fetch_and_verify_metadata(problem_slug, platform)
        search_slug = meta["slug"] if meta else problem_slug
        if platform == "LeetCode" and not meta:
            search_slug = normalize_problem_name(problem_slug)
        if platform == "Codeforces" and not meta:
            search_slug = problem_slug.strip().upper()
        if platform == "GeeksforGeeks" and not meta:
            # Use centralized parsing if metadata fetch failed
            search_slug = parse_gfg_slug(problem_slug)

        await self.bot.db.unset_potd(search_slug, platform)
        await interaction.followup.send(f"✅ Removed POTD status from `{search_slug}`.")
    # ==================================================================
    # 7. Remove all POTD
    # ==================================================================
    @app_commands.command(name="clearpotd", description="Remove POTD status from ALL problems (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_potd(self, interaction: discord.Interaction):
        """Removes POTD status from all active POTDs"""
        await interaction.response.defer(ephemeral=True)
        try:
            cursor = await self.bot.db.db.execute("UPDATE Problems SET is_potd = 0, potd_date = NULL WHERE is_potd = 1")
            await self.bot.db.db.commit()
            count = cursor.rowcount
            if count > 0:
                await interaction.followup.send(embed=discord.Embed(title="✅ POTD Cleared", description=f"Removed POTD status from **{count}** problems.", color=config.COLOR_SUCCESS))
            else:
                await interaction.followup.send(embed=discord.Embed(title="ℹ️ No Active POTDs", description="There were no active POTD problems to clear.", color=config.COLOR_INFO))
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # ==================================================================
    # 8. Problem Bank View
    # ==================================================================
    @app_commands.command(name="problembank", description="Admin: View the problem queue status")
    @app_commands.checks.has_permissions(administrator=True)
    async def problem_bank(self, interaction: discord.Interaction):
        """View upcoming problems in the queue"""
        await interaction.response.defer(ephemeral=True)
        
        status = await self.bot.db.get_queue_status()
        preview_rows = await self.bot.db.get_queue_preview(limit=10)
        
        embed = discord.Embed(title="📚 Problem Bank Status", color=config.COLOR_INFO)
        stats = f"**Year 1:** {status.get('1', 0)}\n**Year 2:** {status.get('2', 0)}\n**Year 3:** {status.get('3', 0)}"
        embed.add_field(name="Queue Counts", value=stats, inline=False)
        
        if preview_rows:
            preview_text = ""
            for row in preview_rows:
                # row is tuple: (problem_title, academic_year, platform)
                preview_text += f"• `Y{row[1]}` {row[0]} ({row[2]})\n"
            embed.add_field(name="Next Up (Mixed)", value=preview_text, inline=False)
        else:
            embed.add_field(name="Next Up", value="*Queue is empty*", inline=False)
            
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Problems(bot))