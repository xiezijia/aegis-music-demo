from fastapi import APIRouter, HTTPException, Depends
import aiosqlite
from database import get_db
from models import FeedbackRequest
from routers.auth import current_user

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _require_teacher(user):
    if user["role"] != "teacher":
        raise HTTPException(403, "仅教师可访问")


@router.get("/submissions")
async def all_submissions(
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    _require_teacher(user)
    async with db.execute(
        """SELECT t.*, u.display_name,
               (SELECT comment FROM feedbacks f WHERE f.track_id=t.id ORDER BY f.id DESC LIMIT 1) as feedback,
               (SELECT score  FROM feedbacks f WHERE f.track_id=t.id ORDER BY f.id DESC LIMIT 1) as score
           FROM tracks t JOIN users u ON t.user_id=u.id
           WHERE t.submitted=1
           ORDER BY t.created_at DESC"""
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/student/{student_id}/tracks")
async def student_tracks(
    student_id: int,
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    _require_teacher(user)
    async with db.execute(
        """SELECT t.*,
               (SELECT comment FROM feedbacks f WHERE f.track_id=t.id ORDER BY f.id DESC LIMIT 1) as feedback
           FROM tracks t
           WHERE t.user_id=?
           ORDER BY t.created_at ASC""",
        (student_id,)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/students")
async def students_list(
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    _require_teacher(user)
    async with db.execute(
        """SELECT u.id, u.display_name, u.username,
               COUNT(t.id) as track_count,
               SUM(t.submitted) as submitted_count
           FROM users u
           LEFT JOIN tracks t ON t.user_id=u.id
           WHERE u.role='student'
           GROUP BY u.id
           ORDER BY u.display_name"""
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/feedback")
async def give_feedback(
    req: FeedbackRequest,
    user=Depends(current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    _require_teacher(user)
    await db.execute(
        "INSERT INTO feedbacks (track_id, teacher_id, comment, score) VALUES (?,?,?,?)",
        (req.track_id, user["id"], req.comment, req.score)
    )
    await db.commit()
    return {"ok": True}
