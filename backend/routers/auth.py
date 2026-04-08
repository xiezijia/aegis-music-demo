from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiosqlite, os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from database import get_db
from models import LoginRequest, TokenResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "aegis-demo-secret")
ALGORITHM  = "HS256"
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))


def make_token(user_id: int, role: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, SECRET_KEY, ALGORITHM)


async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: aiosqlite.Connection = Depends(get_db)
):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token")

    async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT * FROM users WHERE username=?", (req.username,)
    ) as cur:
        row = await cur.fetchone()

    if not row or not pwd_ctx.verify(req.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = make_token(row["id"], row["role"])
    return TokenResponse(
        access_token=token,
        role=row["role"],
        display_name=row["display_name"],
        user_id=row["id"]
    )


@router.get("/me")
async def me(user=Depends(current_user)):
    return {"id": user["id"], "role": user["role"], "display_name": user["display_name"]}
