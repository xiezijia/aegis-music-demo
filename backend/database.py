import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "./aegis_demo.db")

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',   -- 'student' | 'teacher'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    style TEXT,
    lyrics TEXT,
    audio_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | generating | done | error
    version INTEGER NOT NULL DEFAULT 1,
    parent_id INTEGER REFERENCES tracks(id), -- 上一个版本
    submitted INTEGER NOT NULL DEFAULT 0,    -- 是否提交给老师
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    comment TEXT NOT NULL,
    score INTEGER,                           -- 0-100，可选
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()
