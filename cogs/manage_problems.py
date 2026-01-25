"""
CLI Tool to manage the Problem Bank (data/problem_bank.json)
Usage: python manage_problems.py
"""

import json
import os
from pathlib import Path

BANK_PATH = Path("data/problem_bank.json")

def load_bank():
    if not BANK_PATH.exists():
        return {"topics": []}
    with open(BANK_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_bank(data):
    with open(BANK_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("✅ Saved successfully!")

def add_problem():
    data = load_bank()
    
    print("\n--- Select Topic ---")
    topics = data.get("topics", [])
    for i, t in enumerate(topics):
        print(f"{i+1}. {t['name']}")
    print(f"{len(topics)+1}. [Create New Topic]")
    
    try:
        choice = int(input("\nChoice: ")) - 1
    except ValueError:
        print("Invalid input.")
        return

    if choice == len(topics):
        new_topic_name = input("Enter New Topic Name: ")
        topics.append({"name": new_topic_name, "problems": []})
        data["topics"] = topics
        topic_idx = len(topics) - 1
    elif 0 <= choice < len(topics):
        topic_idx = choice
    else:
        print("Invalid choice.")
        return

    print(f"\nAdding to: {topics[topic_idx]['name']}")
    print("-" * 30)
    
    slug = input("Slug (e.g. two-sum): ").strip()
    title = input("Title (e.g. Two Sum): ").strip()
    
    print("Difficulty: (1) Easy, (2) Medium, (3) Hard")
    diff_map = {"1": "Easy", "2": "Medium", "3": "Hard"}
    diff_choice = input("Choice: ")
    difficulty = diff_map.get(diff_choice, "Medium")
    
    url = f"https://leetcode.com/problems/{slug}/"
    print(f"URL generated: {url}")
    
    new_prob = {
        "slug": slug,
        "title": title,
        "difficulty": difficulty,
        "url": url
    }
    
    data["topics"][topic_idx]["problems"].append(new_prob)
    save_bank(data)
    print(f"Problem '{title}' added!")

def main():
    while True:
        print("\n=== Problem Bank Manager ===")
        print("1. Add Problem")
        print("2. Exit")
        choice = input("Select: ")
        
        if choice == "1":
            add_problem()
        elif choice == "2":
            break

if __name__ == "__main__":
    main()