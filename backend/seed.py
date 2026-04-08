"""
初始化 demo 数据：
  - 1 个老师账号
  - 30 个学生账号
  - 每个学生预置 1-2 首已完成的作品（用于演示版本历史）
运行：python seed.py
"""
import asyncio, aiosqlite
from passlib.context import CryptContext
from database import DB_PATH, init_db

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEACHER = {"username": "teacher01", "password": "aegis2026", "display_name": "王老师"}

STUDENTS = [
    {"username": f"stu{i:02d}", "password": "student123", "display_name": name}
    for i, name in enumerate([
        "李同学","王同学","张同学","刘同学","陈同学",
        "杨同学","赵同学","黄同学","周同学","吴同学",
        "徐同学","孙同学","马同学","朱同学","胡同学",
        "郭同学","何同学","高同学","林同学","郑同学",
        "谢同学","罗同学","梁同学","宋同学","唐同学",
        "许同学","韩同学","冯同学","邓同学","曹同学",
    ], start=1)
]

# 预置作品数据（已完成，有 audio_url）
DEMO_TRACKS = [
    {
        "title": "秋风古道",
        "prompt": "忧郁的秋天，带古筝和箫的意境，思念远方的故人",
        "style": "古风 民族 忧郁",
        "lyrics": "秋风吹过古道边，黄叶飘零无人见",
        "audio_url": "https://cdn1.suno.ai/c185e44b-3263-4900-9de5-5005d25082eb.mp3",
        "status": "done", "submitted": 1
    },
    {
        "title": "秋风古道 v2（修改版）",
        "prompt": "忧郁的秋天，古筝主旋律更突出，加入低沉鼓点",
        "style": "古风 民族 忧郁 鼓点",
        "lyrics": "秋风吹过古道边，黄叶飘零无人见，鼓声阵阵入云霄",
        "audio_url": "https://cdn1.suno.ai/2c6b68a4-7a80-4a33-8e71-6cfd93222c23.mp3",
        "status": "done", "submitted": 1
    },
]

DEMO_FEEDBACK = "整体旋律流畅，古筝音色选择很好。建议第二段加入更多留白，让情绪更有层次感。v2 版本鼓点加入效果不错，继续完善歌词意境。"


async def seed():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        # 老师
        hp = pwd_ctx.hash(TEACHER["password"])
        await db.execute(
            "INSERT OR IGNORE INTO users (username, display_name, hashed_password, role) VALUES (?,?,?,'teacher')",
            (TEACHER["username"], TEACHER["display_name"], hp)
        )

        # 学生 + 预置作品（只给前3个学生）
        for i, stu in enumerate(STUDENTS):
            hp = pwd_ctx.hash(stu["password"])
            await db.execute(
                "INSERT OR IGNORE INTO users (username, display_name, hashed_password, role) VALUES (?,?,?,'student')",
                (stu["username"], stu["display_name"], hp)
            )
            await db.commit()

            if i < 3:
                async with db.execute("SELECT id FROM users WHERE username=?", (stu["username"],)) as cur:
                    row = await cur.fetchone()
                uid = row[0]

                parent_id = None
                for v, track in enumerate(DEMO_TRACKS, start=1):
                    async with db.execute(
                        """INSERT OR IGNORE INTO tracks
                           (user_id, title, prompt, style, lyrics, audio_url, status, version, parent_id, submitted)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (uid, track["title"], track["prompt"], track["style"],
                         track["lyrics"], track["audio_url"], track["status"],
                         v, parent_id, track["submitted"])
                    ) as cur:
                        parent_id = cur.lastrowid

                # 给第一个学生加老师评语
                if i == 0:
                    async with db.execute("SELECT id FROM users WHERE username='teacher01'") as cur:
                        teacher_row = await cur.fetchone()
                    tid = teacher_row[0]
                    async with db.execute(
                        "SELECT id FROM tracks WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                    ) as cur:
                        last_track = await cur.fetchone()
                    await db.execute(
                        "INSERT INTO feedbacks (track_id, teacher_id, comment, score) VALUES (?,?,?,?)",
                        (last_track[0], tid, DEMO_FEEDBACK, 88)
                    )

        await db.commit()
        print("✅ Seed 完成")
        print(f"   老师账号：{TEACHER['username']} / {TEACHER['password']}")
        print(f"   学生账号：stu01~stu30 / student123")


if __name__ == "__main__":
    asyncio.run(seed())
