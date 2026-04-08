#!/bin/bash
# AEGIS 智慧音乐教室 Demo 一键启动

echo "🎵 Starting AEGIS Music Demo..."

# 1. 杀掉旧进程
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# 2. 同步 Chrome Suno Cookie（保持 keep-alive 有效）
echo "🔄 Syncing Chrome cookies..."
python3 << 'PYEOF'
import browser_cookie3, json
from pathlib import Path

AUTH_FILE = Path(__file__).parent / "backend/suno_auth.json"

try:
    jar = browser_cookie3.chrome(domain_name=".suno.com")
    cookies = {c.name: c.value for c in jar if not c.is_expired()}
    jar2 = browser_cookie3.chrome(domain_name="auth.suno.com")
    cookies.update({c.name: c.value for c in jar2 if not c.is_expired()})
    
    auth = json.loads(AUTH_FILE.read_text()) if AUTH_FILE.exists() else {}
    if cookies.get('__session'): auth['session_token'] = cookies['__session']
    if cookies.get('__client'):  auth['client_token']  = cookies['__client']
    auth['cookie_str'] = '; '.join(f"{k}={v}" for k,v in cookies.items())
    AUTH_FILE.write_text(json.dumps(auth, indent=2))
    print(f"  ✅ {len(cookies)} cookies synced")
except Exception as e:
    print(f"  ⚠️  cookie sync failed (not critical): {e}")
PYEOF

# 3. 启动后端
echo "🚀 Starting backend..."
cd "$(dirname "$0")/backend"
/Users/xzj/Library/Python/3.9/bin/uvicorn main:app --port 8000 > /tmp/aegis_backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 4

# 4. 检查后端
python3 -c "
import http.client, json
try:
    c = http.client.HTTPConnection('127.0.0.1', 8000, timeout=5)
    c.request('GET', '/')
    r = c.getresponse()
    d = json.loads(r.read())
    print(f'  ✅ Backend: {d[\"status\"]} | token: {d[\"suno_token\"]}')
except Exception as e:
    print(f'  ❌ Backend error: {e}')
" 2>&1

# 5. 启动前端
echo "🌐 Starting frontend..."
cd "$(dirname "$0")/frontend"
npm run dev > /tmp/aegis_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
sleep 3

echo ""
echo "================================================"
echo "  🎵 AEGIS 智慧音乐教室 Demo 已就绪"
echo "  浏览器打开: http://localhost:5173"
echo "  老师账号: teacher01 / aegis2026"
echo "  学生账号: stu01~stu30 / student123"
echo "================================================"

open http://localhost:5173
