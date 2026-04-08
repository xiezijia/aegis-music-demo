from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from services.suno import suno_cookie, init_keep_alive, get_token

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    suno_cookie.load_from_file()   # 加载 auth
    init_keep_alive()              # 启动 asyncio 后台 token 续活任务
    yield

app = FastAPI(title="AEGIS 音乐大模型 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import auth, music, teacher
app.include_router(auth.router)
app.include_router(music.router)
app.include_router(teacher.router)

@app.get("/")
async def root():
    t = get_token()
    return {
        "name": "AEGIS Music API",
        "status": "running",
        "suno_token": "active" if t else "no token",
        "token_preview": t[:20] + "..." if t else "",
    }

@app.get("/api/config")
async def config():
    """前端读取运行时配置（如是否 mock 模式）"""
    import os
    return {"suno_provider": os.getenv("SUNO_PROVIDER", "browser")}
