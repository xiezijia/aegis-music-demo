from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ── Auth ───────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str
    user_id: int

# ── Music Generation ───────────────────────────
class GenerateRequest(BaseModel):
    title: str
    prompt: str             # 情绪/场景描述，中文
    style: Optional[str] = ""    # 风格标签，如 "古风 民族 忧郁"
    lyrics: Optional[str] = ""   # 歌词（可选）
    parent_id: Optional[int] = None  # 基于哪个版本修改

class TrackOut(BaseModel):
    id: int
    user_id: int
    title: str
    prompt: str
    style: Optional[str]
    lyrics: Optional[str]
    audio_url: Optional[str]
    status: str
    version: int
    parent_id: Optional[int]
    submitted: bool
    created_at: str
    display_name: Optional[str] = None  # join users
    feedback: Optional[str] = None      # join feedbacks

# ── Teacher Feedback ───────────────────────────
class FeedbackRequest(BaseModel):
    track_id: int
    comment: str
    score: Optional[int] = None
