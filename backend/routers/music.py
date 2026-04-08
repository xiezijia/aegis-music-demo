from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import aiosqlite
from database import get_db
from models import GenerateRequest, TrackOut
from routers.auth import current_user
from services.suno import generate_music

router = APIRouter(prefix="/api/music", tags=["music"])


async def _do_generate(track_id: int, prompt: str, style: str, lyrics: str, db_path: str):
    """后台任务：调 Suno，完成后更新数据库"""
    import aiosqlite as _aio
    try:
        result = await generate_music(prompt, style, lyrics)
        audio_url = result["audio_url"]
        status = "done"
    except Exception as e:
        audio_url = ""
        status = "error"

    async with _aio.connect(db_path) as db:
        await db.execute(
            "UPDATE tracks SET audio_url=?, status=? WHERE id=?",
            (audio_url, status, track_id)
        )
        await db.commit()


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    bg: BackgroundTasks,
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    # 计算版本号
    version = 1
    if req.parent_id:
        async with db.execute(
            "SELECT version FROM tracks WHERE id=?", (req.parent_id,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            version = row["version"] + 1

    # 插入 pending 记录
    async with db.execute(
        """INSERT INTO tracks (user_id, title, prompt, style, lyrics, status, version, parent_id)
           VALUES (?, ?, ?, ?, ?, 'generating', ?, ?)""",
        (user["id"], req.title, req.prompt, req.style, req.lyrics, version, req.parent_id)
    ) as cur:
        track_id = cur.lastrowid
    await db.commit()

    # 异步生成
    from database import DB_PATH
    bg.add_task(_do_generate, track_id, req.prompt, req.style or "", req.lyrics or "", DB_PATH)

    return {"track_id": track_id, "status": "generating"}


@router.get("/status/{track_id}")
async def track_status(
    track_id: int,
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute(
        "SELECT id, status, audio_url FROM tracks WHERE id=? AND user_id=?",
        (track_id, user["id"])
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Track not found")
    return dict(row)


@router.get("/my-tracks")
async def my_tracks(
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute(
        """SELECT t.*, u.display_name,
               (SELECT comment FROM feedbacks f WHERE f.track_id=t.id ORDER BY f.id DESC LIMIT 1) as feedback
           FROM tracks t JOIN users u ON t.user_id=u.id
           WHERE t.user_id=?
           ORDER BY t.created_at DESC""",
        (user["id"],)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/submit/{track_id}")
async def submit_track(
    track_id: int,
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    await db.execute(
        "UPDATE tracks SET submitted=1 WHERE id=? AND user_id=?",
        (track_id, user["id"])
    )
    await db.commit()
    return {"ok": True}
