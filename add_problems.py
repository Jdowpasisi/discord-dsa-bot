import asyncio
import json
import os
from pathlib import Path
from utils.leetcode_api import get_leetcode_api, close_leetcode_api
from utils.logic import normalize_problem_name

FILE_PATH = Path("data/problem_bank.json")

def load_queue():
    if not FILE_PATH.exists():
        return {"queue": []}
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_queue(data):
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved! Queue size: {len(data['queue'])} days.")

async def fetch_problem_details(api, slug, year_label):
    """Fetch metadata and return a formatted dict"""
    clean_slug = normalize_problem_name(slug)
    print(f"   🔎 Fetching {year_label}: {clean_slug}...")
    
    # Add a small delay to be nice to the API
    await asyncio.sleep(0.5)
    
    meta = await api.get_problem_metadata(clean_slug)
    if not meta:
        print(f"   ❌ Error: '{clean_slug}' not found on LeetCode.")
        return None
        
    return {
        "slug": meta.title_slug,
        "title": meta.title,
        "difficulty": year_label, # Storing "1st Year" directly
        "url": f"https://leetcode.com/problems/{meta.title_slug}/"
    }

async def add_daily_set():
    print("\n--- 📅 Add a New Daily Set (3 Problems) ---")
    
    s1 = input("1st Year Slug: ").strip()
    s2 = input("2nd Year Slug: ").strip()
    s3 = input("3rd Year Slug: ").strip()
    
    if not s1 or not s2 or not s3:
        print("❌ All 3 problems are required.")
        return

    # Get a fresh API instance
    api = get_leetcode_api()
    
    # Fetch all 3
    p1 = await fetch_problem_details(api, s1, "1st Year")
    if not p1: return # Fail fast if 1st invalid
    
    p2 = await fetch_problem_details(api, s2, "2nd Year")
    if not p2: return
    
    p3 = await fetch_problem_details(api, s3, "3rd Year")
    if not p3: return
    
    # Create the set
    day_set = [p1, p2, p3]
    
    data = load_queue()
    data["queue"].append(day_set)
    save_queue(data)
    print("✨ Successfully added set to queue!")

async def main():
    print("🚀 Bulk Problem Adder initialized.")
    while True:
        await add_daily_set()
        
        # CRITICAL FIX: Close the session after every batch.
        # This prevents "Connection Closed" errors when you wait too long between inputs.
        await close_leetcode_api()
        
        cont = input("\nAdd another day? (y/n): ").lower()
        if cont != 'y':
            break
    
    print("👋 Exiting...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")