-- LeetCode Discord Bot Database Schema
-- SQLite Database

-- Users Table: Tracks Discord users and their statistics
CREATE TABLE IF NOT EXISTS Users (
    discord_id INTEGER PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    weekly_streak INTEGER DEFAULT 0,
    last_submission_date TEXT,  -- ISO format: YYYY-MM-DD HH:MM:SS
    last_week_submitted TEXT    -- Format: YYYY-WW (e.g., "2026-03")
);

-- Problems Table: Stores LeetCode problem information
CREATE TABLE IF NOT EXISTS Problems (
    problem_slug TEXT PRIMARY KEY,
    difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy', 'Medium', 'Hard')),
    topic TEXT NOT NULL,
    date_posted TEXT NOT NULL  -- ISO format: YYYY-MM-DD
);

-- Submissions Table: Records user submissions for problems
CREATE TABLE IF NOT EXISTS Submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    problem_slug TEXT NOT NULL,
    submission_date TEXT NOT NULL,  -- ISO format: YYYY-MM-DD HH:MM:SS
    points_awarded INTEGER NOT NULL,
    FOREIGN KEY (discord_id) REFERENCES Users(discord_id) ON DELETE CASCADE,
    FOREIGN KEY (problem_slug) REFERENCES Problems(problem_slug) ON DELETE CASCADE
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_submissions_discord_id ON Submissions(discord_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem_slug ON Submissions(problem_slug);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON Submissions(submission_date);
CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON Problems(difficulty);
CREATE INDEX IF NOT EXISTS idx_problems_date_posted ON Problems(date_posted);
