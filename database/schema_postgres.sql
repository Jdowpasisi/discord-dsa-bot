-- LeetCode Discord Bot Database Schema
-- PostgreSQL Database (Supabase Compatible)

-- Users Table: Tracks Discord users and their statistics
CREATE TABLE IF NOT EXISTS Users (
    discord_id BIGINT PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    weekly_streak INTEGER DEFAULT 0,
    last_submission_date TEXT,  -- ISO format: YYYY-MM-DD HH:MM:SS
    last_week_submitted TEXT,   -- Format: YYYY-WW (e.g., "2026-03")
    student_year TEXT DEFAULT 'General',  -- Valid values: "1", "2", "3", "4", "General"
    leetcode_username TEXT UNIQUE, -- User's LeetCode username
    codeforces_handle TEXT,
    gfg_handle TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Problems Table: Stores problem information across platforms
CREATE TABLE IF NOT EXISTS Problems (
    id SERIAL,  -- Auto-increment for ordering (replaces SQLite rowid)
    problem_slug TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'LeetCode',
    problem_title TEXT,
    difficulty TEXT,  -- Actual problem difficulty: Easy, Medium, Hard
    academic_year TEXT,  -- Academic year level: "1", "2", "3"
    topic TEXT NOT NULL,
    date_posted TEXT,  -- DEPRECATED: Keep for backwards compatibility
    is_potd INTEGER DEFAULT 0,  -- 1 if currently POTD, 0 otherwise
    potd_date TEXT,  -- Date when set as POTD (YYYY-MM-DD)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (problem_slug, platform)
);

-- Submissions Table: Records user submissions for problems
CREATE TABLE IF NOT EXISTS Submissions (
    submission_id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    problem_slug TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'LeetCode',
    submission_date TEXT NOT NULL,  -- ISO format: YYYY-MM-DD HH:MM:SS
    points_awarded INTEGER NOT NULL,
    verification_status TEXT DEFAULT 'Verified',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (discord_id) REFERENCES Users(discord_id) ON DELETE CASCADE,
    CONSTRAINT fk_problem FOREIGN KEY (problem_slug, platform) REFERENCES Problems(problem_slug, platform) ON DELETE CASCADE
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_submissions_discord_id ON Submissions(discord_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem_slug ON Submissions(problem_slug);
CREATE INDEX IF NOT EXISTS idx_submissions_platform ON Submissions(platform);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON Submissions(submission_date);
CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON Problems(difficulty);
CREATE INDEX IF NOT EXISTS idx_problems_academic_year ON Problems(academic_year);
CREATE INDEX IF NOT EXISTS idx_problems_date_posted ON Problems(date_posted);
CREATE INDEX IF NOT EXISTS idx_problems_platform ON Problems(platform);
CREATE INDEX IF NOT EXISTS idx_problems_slug_platform ON Problems(problem_slug, platform);
CREATE INDEX IF NOT EXISTS idx_problems_is_potd ON Problems(is_potd);
CREATE INDEX IF NOT EXISTS idx_problems_potd_date ON Problems(potd_date);
CREATE INDEX IF NOT EXISTS idx_problems_id ON Problems(id);
