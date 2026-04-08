#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  AEGIS 智慧音乐教室 — 一键测试脚本
#  用法: bash test.sh
#  覆盖: 环境 → 服务 → API → 权限 → Keep-Alive 监控
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_URL="http://127.0.0.1:8000"

# ── 颜色 ──────────────────────────────────────────────────────
G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"
B="\033[0;34m"; C="\033[0;36m"; W="\033[1;37m"; N="\033[0m"

PASS=0; FAIL=0; WARN=0
ok()   { echo -e "  ${G}✅ $*${N}";  PASS=$((PASS+1)); }
fail() { echo -e "  ${R}❌ $*${N}";  FAIL=$((FAIL+1)); }
warn() { echo -e "  ${Y}⚠️  $*${N}"; WARN=$((WARN+1)); }
info() { echo -e "  ${C}→  $*${N}"; }
section() {
  echo ""; echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
  echo -e "${W}  $1${N}"
  echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
}

# ── HTTP 工具（用 Python，无沙盒限制）────────────────────────
py_http() {
  python3 - "$@" << 'PYEOF'
import sys, json, http.client, urllib.parse

method = sys.argv[1]      # GET | POST
url    = sys.argv[2]      # http://127.0.0.1:8000/...
data   = sys.argv[3] if len(sys.argv) > 3 else ""
token  = sys.argv[4] if len(sys.argv) > 4 else ""

parsed = urllib.parse.urlparse(url)
conn   = http.client.HTTPConnection(parsed.netloc, timeout=8)
headers = {"Content-Type": "application/json"}
if token: headers["Authorization"] = f"Bearer {token}"

try:
  if method == "POST":
    conn.request("POST", parsed.path, body=data.encode(), headers=headers)
  else:
    conn.request("GET", parsed.path, headers=headers)
  r = conn.getresponse()
  body = r.read().decode()
  # 输出: STATUS_CODE\nBODY
  print(r.status)
  print(body)
  sys.exit(0 if r.status < 300 else 1)
except Exception as e:
  print(0)
  print(f'{{"error":"{e}"}}')
  sys.exit(1)
PYEOF
}

# 解析 HTTP 输出的 status code 和 body
http_code() { echo "$1" | head -1; }
http_body() { echo "$1" | tail -n +2; }
json_val()  { echo "$1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split('\n',1)[1] if '\n' in sys.stdin.read() else sys.stdin.read()); print(d.get('$2',''))" 2>/dev/null; }

# 简化版 json 提取（接受 body 字符串）
jval() { echo "$2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }

# ══════════════════════════════════════════════════════════════
section "第一步：环境检查"
# ══════════════════════════════════════════════════════════════

# Python 版本
PY_VER=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
python3 -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null \
  && ok "Python $PY_VER" || fail "Python 版本 $PY_VER 需要 3.9+"

# Node
NODE_VER=$(node --version 2>/dev/null)
[ -n "$NODE_VER" ] && ok "Node.js $NODE_VER" || fail "Node.js 未安装"

# Python 依赖
for pkg in fastapi uvicorn curl_cffi browser_cookie3; do
  python3 -c "import $pkg" 2>/dev/null \
    && ok "Python: $pkg" \
    || fail "Python: $pkg 缺失 → python3 setup.py"
done

# node_modules
[ -d "$ROOT/frontend/node_modules" ] \
  && ok "frontend/node_modules 存在" \
  || fail "frontend/node_modules 缺失 → cd frontend && npm install"

# .env
if [ -f "$ROOT/backend/.env" ]; then
  PROVIDER=$(grep "^SUNO_PROVIDER" "$ROOT/backend/.env" | cut -d= -f2)
  ok "backend/.env (SUNO_PROVIDER=$PROVIDER)"
else
  fail "backend/.env 缺失 → cp backend/.env.example backend/.env"
fi

# suno_auth.json
if [ -f "$ROOT/backend/suno_auth.json" ]; then
  CLIENT_OK=$(python3 -c "import json; d=json.load(open('$ROOT/backend/suno_auth.json')); print('ok' if d.get('client_token') else 'empty')" 2>/dev/null)
  [ "$CLIENT_OK" = "ok" ] \
    && ok "suno_auth.json: cookie 存在" \
    || warn "suno_auth.json: client_token 为空 → python3 setup.py"
else
  warn "suno_auth.json 不存在（mock 模式下不影响功能）"
fi

# 有严重失败就停止
if [ $FAIL -gt 0 ]; then
  echo ""; fail "环境有 $FAIL 项不通过，请修复后重试"; exit 1
fi

# ══════════════════════════════════════════════════════════════
section "第二步：确认后端服务在线"
# ══════════════════════════════════════════════════════════════

# 检查后端是否在运行
RESP=$(py_http GET "$BACKEND_URL/"); CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)

if [ "$CODE" = "200" ] && echo "$BODY" | grep -q "running"; then
  SUNO_TOKEN=$(jval "suno_token" "$BODY")
  ok "后端在线 (suno_token=$SUNO_TOKEN)"
else
  warn "后端未运行，自动启动..."
  pkill -f "uvicorn main:app" 2>/dev/null; sleep 1
  cd "$ROOT/backend" && \
    python3 -m uvicorn main:app --port 8000 --no-access-log \
    > /tmp/aegis_backend.log 2>&1 &
  info "等待启动（8 秒）..."
  sleep 8

  RESP=$(py_http GET "$BACKEND_URL/"); CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  if [ "$CODE" = "200" ] && echo "$BODY" | grep -q "running"; then
    SUNO_TOKEN=$(jval "suno_token" "$BODY")
    ok "后端已启动 (suno_token=$SUNO_TOKEN)"
  else
    fail "后端启动失败，日志如下:"
    tail -5 /tmp/aegis_backend.log 2>/dev/null | sed 's/^/    /'
    exit 1
  fi
fi

# 前端（仅提示，不强制）
if python3 -c "
import http.client
c = http.client.HTTPConnection('127.0.0.1', 5173, timeout=3)
c.request('GET', '/')
c.getresponse()
" 2>/dev/null; then
  ok "前端在线 (localhost:5173)"
else
  warn "前端未运行（浏览器 UI 需手动启动: cd frontend && npm run dev）"
fi

# ══════════════════════════════════════════════════════════════
section "第三步：后端 API 测试"
# ══════════════════════════════════════════════════════════════

# 3-1 学生登录
info "学生登录 stu01..."
RESP=$(py_http POST "$BACKEND_URL/api/auth/login" '{"username":"stu01","password":"student123"}')
CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
STU_TOKEN=$(jval "access_token" "$BODY")
STU_ROLE=$(jval "role" "$BODY")
STU_NAME=$(jval "display_name" "$BODY")
if [ "$CODE" = "200" ] && [ "$STU_ROLE" = "student" ]; then
  ok "学生登录: $STU_NAME (role=$STU_ROLE)"
else
  fail "学生登录失败 HTTP=$CODE → $BODY"; STU_TOKEN=""
fi

# 3-2 老师登录
info "老师登录 teacher01..."
RESP=$(py_http POST "$BACKEND_URL/api/auth/login" '{"username":"teacher01","password":"aegis2026"}')
CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
TCH_TOKEN=$(jval "access_token" "$BODY")
TCH_ROLE=$(jval "role" "$BODY")
if [ "$CODE" = "200" ] && [ "$TCH_ROLE" = "teacher" ]; then
  ok "老师登录成功 (role=$TCH_ROLE)"
else
  fail "老师登录失败 HTTP=$CODE"; TCH_TOKEN=""
fi

# 3-3 学生作品列表
if [ -n "$STU_TOKEN" ]; then
  info "拉取学生作品列表..."
  RESP=$(py_http GET "$BACKEND_URL/api/music/my-tracks" "" "$STU_TOKEN")
  CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
  if [ "$CODE" = "200" ] && [ "${COUNT:-0}" -gt 0 ] 2>/dev/null; then
    ok "作品列表: $COUNT 条"
  elif [ "${COUNT:-0}" -eq 0 ] 2>/dev/null; then
    warn "作品列表为空 → cd backend && python3 seed.py"
  else
    fail "作品列表请求失败 HTTP=$CODE"
  fi
fi

# 3-4 提交生成
if [ -n "$STU_TOKEN" ]; then
  info "提交生成请求（mock 模式）..."
  RESP=$(py_http POST "$BACKEND_URL/api/music/generate" \
    '{"title":"测试曲目","prompt":"欢快的春天旋律","style":"流行 欢快","lyrics":""}' \
    "$STU_TOKEN")
  CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  TRACK_ID=$(jval "track_id" "$BODY")
  GEN_STATUS=$(jval "status" "$BODY")
  if [ "$CODE" = "200" ] && [ -n "$TRACK_ID" ]; then
    ok "生成任务提交: track_id=$TRACK_ID status=$GEN_STATUS"
  else
    fail "生成请求失败 HTTP=$CODE → $BODY"; TRACK_ID=""
  fi
fi

# 3-5 轮询生成状态
if [ -n "$TRACK_ID" ]; then
  info "等待生成完成（轮询最多 15 秒）..."
  DONE=false
  for i in 1 2 3; do
    sleep 4
    RESP=$(py_http GET "$BACKEND_URL/api/music/status/$TRACK_ID" "" "$STU_TOKEN")
    CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
    FINAL_STATUS=$(jval "status" "$BODY")
    AUDIO_URL=$(jval "audio_url" "$BODY")
    if [ "$FINAL_STATUS" = "done" ] && [ -n "$AUDIO_URL" ]; then
      ok "生成完成! status=done  audio=${AUDIO_URL:0:50}..."
      DONE=true; break
    else
      info "  [${i}] status=$FINAL_STATUS, 继续等待..."
    fi
  done
  [ "$DONE" = "false" ] && fail "生成超时（status=$FINAL_STATUS）→ 检查 /tmp/aegis_backend.log"
fi

# 3-6 老师拉学生列表
if [ -n "$TCH_TOKEN" ]; then
  info "老师拉取学生列表..."
  RESP=$(py_http GET "$BACKEND_URL/api/teacher/students" "" "$TCH_TOKEN")
  CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  STU_COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
  if [ "$CODE" = "200" ] && [ "${STU_COUNT:-0}" -eq 30 ] 2>/dev/null; then
    ok "学生列表: $STU_COUNT 人 ✓"
  elif [ "$CODE" = "200" ]; then
    warn "学生列表: $STU_COUNT 人（期望 30，可能 seed 未完整运行）"
  else
    fail "老师拉学生列表失败 HTTP=$CODE"
  fi
fi

# ══════════════════════════════════════════════════════════════
section "第六步：权限异常测试"
# ══════════════════════════════════════════════════════════════

# 无 token
info "无 token 访问受保护路由..."
RESP=$(py_http GET "$BACKEND_URL/api/music/my-tracks"); CODE=$(echo "$RESP" | head -1)
[ "$CODE" != "200" ] \
  && ok "未认证访问被拒绝 (HTTP $CODE)" \
  || fail "安全漏洞：无 token 也能访问！"

# 学生访问老师路由
if [ -n "$STU_TOKEN" ]; then
  info "学生 token 访问老师路由..."
  RESP=$(py_http GET "$BACKEND_URL/api/teacher/students" "" "$STU_TOKEN")
  CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  [ "$CODE" != "200" ] \
    && ok "角色权限生效 (HTTP $CODE)" \
    || fail "权限漏洞：学生可访问老师路由！"
fi

# 错误密码
info "测试错误密码..."
RESP=$(py_http POST "$BACKEND_URL/api/auth/login" '{"username":"stu01","password":"wrongpass"}')
CODE=$(echo "$RESP" | head -1)
[ "$CODE" != "200" ] \
  && ok "错误密码被拒绝 (HTTP $CODE)" \
  || fail "安全漏洞：错误密码竟然成功！"

# ══════════════════════════════════════════════════════════════
section "第五步：Keep-Alive 监控（35 秒）"
# ══════════════════════════════════════════════════════════════

echo ""
info "每 5 秒检查 suno_token 状态，持续 35 秒..."
echo ""
ALIVE_OK=0; ALIVE_FAIL=0

for i in $(seq 1 7); do
  sleep 5
  RESP=$(py_http GET "$BACKEND_URL/"); CODE=$(echo "$RESP" | head -1); BODY=$(echo "$RESP" | tail -n +2)
  ALIVE_TOK=$(jval "suno_token" "$BODY")
  PREVIEW=$(jval "token_preview" "$BODY")
  TS=$(date +"%H:%M:%S")
  if [ "$CODE" = "200" ] && [ "$ALIVE_TOK" = "active" ]; then
    echo -e "  ${G}[$TS] ✅ $i/7  keep-alive OK  token=${PREVIEW}...${N}"
    ((ALIVE_OK++))
  else
    echo -e "  ${R}[$TS] ❌ $i/7  keep-alive 异常  code=$CODE token=$ALIVE_TOK${N}"
    ((ALIVE_FAIL++))
  fi
done

echo ""
[ $ALIVE_FAIL -eq 0 ] \
  && ok "Keep-Alive 稳定（$ALIVE_OK/7 通过）" \
  || fail "Keep-Alive 不稳定（$ALIVE_FAIL 次异常）→ tail /tmp/aegis_backend.log"

# ══════════════════════════════════════════════════════════════
section "测试结果汇总"
# ══════════════════════════════════════════════════════════════

echo ""
echo -e "  ${W}通过 ${G}$PASS${N}  ${W}失败 ${R}$FAIL${N}  ${W}警告 ${Y}$WARN${N}"
echo ""

if [ $FAIL -eq 0 ] && [ $WARN -le 1 ]; then
  echo -e "  ${G}${W}🎉 全部通过！Demo 可以给学校老师演示了。${N}"
elif [ $FAIL -eq 0 ]; then
  echo -e "  ${Y}${W}⚠️  有 $WARN 项警告，核心功能正常，建议修复后再演示。${N}"
else
  echo -e "  ${R}${W}❌ 有 $FAIL 项失败，请按上方提示修复。${N}"
  echo -e "  ${C}  后端日志: tail -20 /tmp/aegis_backend.log${N}"
fi
echo ""
