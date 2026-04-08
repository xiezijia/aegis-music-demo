"""
Suno 稳定版 v3 - asyncio 后台任务
- Keep-Alive: asyncio.create_task（不用线程，无 selector 冲突）
- 生成: curl_cffi AsyncSession + Android UA + text/plain Content-Type
- Token 刷新: curl_cffi AsyncSession（impersonate=edge101，能过 Clerk TLS）
"""
import os, json, asyncio, time
from pathlib import Path
from curl_cffi.requests import AsyncSession

PROVIDER  = os.getenv("SUNO_PROVIDER", "browser")
# ── Mock URL 映射表 ────────────────────────────────────────────
# 演示模式：按关键词选不同 CDN 音频，让风格之间有明显差异
# 所有 URL 均有 CORS: Access-Control-Allow-Origin: *，可在浏览器直接播放
_MOCK_GENRE_MAP = [
    # 古风 / 民族 / 国风
    (["古风","民族","古筝","二胡","琵琶","箫","笛","国风","传统","山水","水墨","禅"],
     "https://cdn1.suno.ai/c185e44b-3263-4900-9de5-5005d25082eb.mp3"),
    # 摇滚 / 金属 / 重型 / 朋克
    (["摇滚","rock","metal","金属","重金属","朋克","punk","死亡","硬核","hardcore","grunge","浴火","激烈","燃"],
     "https://cdn1.suno.ai/ab43478c-dcba-4c6f-be86-9c51bc679699.mp3"),   # Numb Like This（暗系摇滚）
    # 电子 / 舞曲 / EDM / 现代
    (["电子","edm","dance","舞曲","电","合成器","synth","赛博","cyberpunk","夜店","dj"],
     "https://cdn1.suno.ai/38574285-b6c3-44d0-9a5d-61dfa8ec39b2.mp3"),   # Numb on the Dance Floor（EDM）
    # 流行 / 欢快 / 情歌
    (["流行","pop","欢快","轻快","清新","爱情","温柔","抒情","浪漫","钢琴","吉他","现代"],
     "https://cdn1.suno.ai/2c6b68a4-7a80-4a33-8e71-6cfd93222c23.mp3"),
]
# 默认（爵士、古典、说唱、其他）
_MOCK_DEFAULT_URL = "https://cdn1.suno.ai/3043302b-555f-4086-a875-4200f7ec5a53.mp3"  # 小小肉

def _pick_mock_url(prompt: str, style: str) -> str:
    combined = (prompt + " " + (style or "")).lower()
    for keywords, url in _MOCK_GENRE_MAP:
        if any(k in combined for k in keywords):
            return url
    return _MOCK_DEFAULT_URL

MOCK_URL = _MOCK_DEFAULT_URL  # 向后兼容
AUTH_FILE = Path(__file__).parent.parent / "suno_auth.json"

BASE_URL  = "https://studio-api-prod.suno.com"
CLERK_URL = "https://clerk.suno.com"   # 旧版 clerk 端点，更稳定
CLERK_VER = "4.72.0-snapshot.vc141245"

ANDROID_HEADERS = {
    "x-suno-client":    "Android prerelease-4nt180t 1.0.42",
    "X-Requested-With": "com.suno.android",
    "sec-ch-ua":        '"Chromium";v="130", "Android WebView";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "Content-Type":     "text/plain;charset=UTF-8",
    "Origin":           "https://suno.com",
    "Referer":          "https://suno.com/",
    "User-Agent":       "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
}

# ── 状态（进程内）──────────────────────────────────────────────
_token:      str = ""
_session_id: str = ""
_cookie_str: str = ""
_client_tok: str = ""


def _load_auth():
    global _token, _session_id, _cookie_str, _client_tok
    if not AUTH_FILE.exists(): return
    try:
        with open(AUTH_FILE) as f: data = json.load(f)
        _token      = data.get("session_token", "")
        _session_id = data.get("sessionid", data.get("session_id", ""))
        _cookie_str = data.get("cookie_str", "")
        _client_tok = data.get("client_token", "")
        print(f"✅ Auth loaded: sid={_session_id[:20]}... token={'ok' if _token else 'empty'}")
    except Exception as e:
        print(f"⚠️  auth load error: {e}")


def _save_auth():
    try:
        data = {}
        if AUTH_FILE.exists():
            with open(AUTH_FILE) as f: data = json.load(f)
        data.update({"session_token": _token, "cookie_str": _cookie_str, "sessionid": _session_id})
        with open(AUTH_FILE, "w") as f: json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  auth save error: {e}")


# ── asyncio keep-alive task ───────────────────────────────────

async def _refresh_token() -> bool:
    global _token, _session_id, _cookie_str

    # Step A: 先拿 session_id（如果没有）
    if not _session_id:
        try:
            async with AsyncSession(impersonate="edge101") as s:
                r = await s.get(
                    f"{CLERK_URL}/v1/client?_clerk_js_version={CLERK_VER}",
                    headers={"Cookie": _cookie_str, "Authorization": _client_tok,
                             "User-Agent": "Mozilla/5.0"},
                    timeout=15
                )
                if r.status_code == 200:
                    sid = (r.json().get("response") or {}).get("last_active_session_id", "")
                    if sid:
                        _session_id = sid
                        print(f"✅ Got session_id: {sid[:20]}...")
        except Exception as e:
            print(f"  get_sid error: {e}")

    if not _session_id:
        # fallback: 从 Playwright 浏览器拿
        try:
            import subprocess
            r = subprocess.run(
                ["npx", "--package", "@playwright/cli", "playwright-cli", "cookie-get", "__session"],
                capture_output=True, text=True, timeout=10
            )
            if "__session=" in r.stdout:
                jwt = r.stdout.split("__session=")[1].split(" (domain")[0].strip()
                if jwt and len(jwt) > 100:
                    _token = jwt
                    _save_auth()
                    print("✅ Token from Playwright browser")
                    return True
        except Exception:
            pass
        return False

    # Step B: 换 JWT
    try:
        async with AsyncSession(impersonate="edge101") as s:
            r = await s.post(
                f"{CLERK_URL}/v1/client/sessions/{_session_id}/tokens"
                f"?_clerk_js_version={CLERK_VER}",
                data="",
                headers={"Cookie": _cookie_str, "Authorization": _client_tok,
                         "User-Agent": "Mozilla/5.0",
                         "Content-Type": "application/x-www-form-urlencoded"},
                timeout=15
            )
            if r.status_code == 200:
                jwt = r.json().get("jwt", "")
                if jwt:
                    _token = jwt
                    # 更新 Set-Cookie
                    sc = r.headers.get("set-cookie", "")
                    if sc: _cookie_str = sc  # 简化处理
                    _save_auth()
                    return True
            elif r.status_code == 401:
                # session 可能失效，清空让 Step A 重新获取
                _session_id = ""
            print(f"  token refresh HTTP {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"  token refresh error: {e}")
    return False


async def keep_alive_loop():
    """asyncio 后台任务，5 秒刷新一次 JWT"""
    print("🔄 keep-alive task started")
    fail = 0
    while True:
        ok = await _refresh_token()
        if ok:
            fail = 0
        else:
            fail += 1
            if fail == 1: print(f"⚠️  token refresh failed")
        await asyncio.sleep(5 if ok else 30)


def init_keep_alive():
    """在 FastAPI lifespan 里调用"""
    _load_auth()
    asyncio.create_task(keep_alive_loop())


# ── 公开接口 ──────────────────────────────────────────────────

def get_token() -> str:
    return _token


async def generate_music(prompt: str, style: str = "", lyrics: str = "") -> dict:
    if PROVIDER == "mock":
        await asyncio.sleep(2)
        return {"audio_url": _pick_mock_url(prompt, style), "task_id": "mock-001", "title": ""}
    if PROVIDER == "goapi":
        return await _goapi_generate(prompt, style, lyrics)
    return await _direct_generate(prompt, style, lyrics)


async def _direct_generate(prompt: str, style: str, lyrics: str) -> dict:
    token = _token
    if not token:
        await _refresh_token()
        token = _token
        if not token:
            raise RuntimeError("No Suno JWT — check suno_auth.json and keep-alive")

    headers = {**ANDROID_HEADERS, "Authorization": f"Bearer {token}"}

    async with AsyncSession(impersonate="edge101") as s:
        # 1. captcha check
        try:
            ck = await s.post(f"{BASE_URL}/api/c/check",
                data=b'{"ctype":"generation"}', headers=headers, timeout=10)
            captcha_req = ck.status_code == 200 and ck.json().get("required", False)
            print(f"  c/check → {ck.status_code}, captcha_required={captcha_req}")
        except Exception as e:
            print(f"  c/check error: {e}")
            captcha_req = True

        if captcha_req:
            raise RuntimeError(
                "hCaptcha required. Set SUNO_PROVIDER=mock for demo, "
                "or SUNO_PROVIDER=goapi with GoAPI key."
            )

        # 2. 生成
        payload = json.dumps({
            "gpt_description_prompt": prompt,
            "tags": style or "",
            "mv": "chirp-v3-5",
            "prompt": lyrics or "",
            "make_instrumental": not bool((lyrics or "").strip()),
            "generation_type": "TEXT",
            "token": None,
        }).encode()
        print(f"🎵 Generating: {prompt[:50]}")
        r = await s.post(f"{BASE_URL}/api/generate/v2/",
            data=payload, headers=headers, timeout=30)

        if r.status_code == 401:
            await _refresh_token()
            headers["Authorization"] = f"Bearer {_token}"
            r = await s.post(f"{BASE_URL}/api/generate/v2/",
                data=payload, headers=headers, timeout=30)

        if r.status_code != 200:
            raise RuntimeError(f"Generate HTTP {r.status_code}: {r.text[:200]}")

        clips = r.json().get("clips", [])
        if not clips:
            raise RuntimeError(f"No clips: {r.text[:200]}")

        clip_ids  = [c["id"] for c in clips]
        ids_param = "%2C".join(clip_ids)
        print(f"   Clip IDs: {clip_ids}")

        # 3. 精确轮询
        for tick in range(36):
            await asyncio.sleep(5)
            try:
                poll = await s.get(f"{BASE_URL}/api/feed/?ids={ids_param}",
                    headers=headers, timeout=15)
                if poll.status_code == 200:
                    for clip in poll.json():
                        st = clip.get("status", "")
                        print(f"  [{tick*5}s] {clip.get('id','')[:8]}... → {st}")
                        if st == "complete" and clip.get("audio_url"):
                            print(f"✅ Done: {clip.get('title','')}")
                            return {
                                "audio_url": clip["audio_url"],
                                "task_id":   clip["id"],
                                "title":     clip.get("title", prompt[:30]),
                                "image_url": clip.get("image_url", ""),
                            }
                        if st in ("error", "failed"):
                            raise RuntimeError("Clip generation failed")
            except RuntimeError: raise
            except Exception as e:
                print(f"  poll error: {e}")

    raise TimeoutError("Suno generation timed out after 3 min")


async def _goapi_generate(prompt: str, style: str, lyrics: str) -> dict:
    import httpx
    key = os.getenv("GOAPI_KEY", "")
    if not key: raise RuntimeError("GOAPI_KEY not set")
    p = {"model":"chirp-v3-5","prompt":lyrics or "","tags":style,
         "title":prompt[:50],"make_instrumental":not bool(lyrics),
         "gpt_description_prompt":prompt}
    hdrs = {"x-api-key":key,"Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=60) as h:
        r = await h.post("https://api.goapi.ai/api/suno/v1/music", json=p, headers=hdrs)
        r.raise_for_status()
        tid = r.json()["data"]["task_id"]
        for _ in range(36):
            await asyncio.sleep(5)
            pl = await h.get(f"https://api.goapi.ai/api/suno/v1/music/{tid}", headers=hdrs)
            d = pl.json().get("data", {})
            if d.get("status") == "completed":
                clips = d.get("clips", [])
                if clips: return {"audio_url": clips[0]["audio_url"], "task_id": tid}
    raise TimeoutError("GoAPI timed out")


# ── 兼容 suno_cookie 接口（main.py 用到）──────────────────────
class _CompatCookie:
    @property
    def token(self): return _token
    def load_from_file(self, path=None): _load_auth()
    def start(self): pass  # init_keep_alive() 在 lifespan 里调

suno_cookie = _CompatCookie()
