#!/usr/bin/env python3
"""
AEGIS 智慧音乐教室 Demo — 首次安装脚本
运行：python3 setup.py
"""
import os, sys, subprocess, shutil
from pathlib import Path

ROOT    = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

def run(cmd, cwd=None, check=True):
    print(f"  $ {cmd}")
    return subprocess.run(cmd, shell=True, cwd=cwd, check=check)

def step(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print('─'*50)

# ─── 1. Python 依赖 ────────────────────────────────────────────
step("1/5  安装 Python 依赖")
run(f"{sys.executable} -m pip install -r requirements.txt -q", cwd=BACKEND)
run(f"{sys.executable} -m pip install browser-cookie3 curl_cffi -q")

# ─── 2. Node 依赖 ──────────────────────────────────────────────
step("2/5  安装前端依赖 (npm install)")
run("npm install", cwd=FRONTEND)

# ─── 3. 环境变量 ──────────────────────────────────────────────
step("3/5  创建 .env 文件")
env_file = BACKEND / ".env"
if not env_file.exists():
    shutil.copy(BACKEND / ".env.example", env_file)
    print("  ✅ backend/.env 已创建（默认 SUNO_PROVIDER=mock）")
else:
    print("  ⏭  backend/.env 已存在，跳过")

# ─── 4. 从 Chrome 同步 Suno Cookie ──────────────────────────
step("4/5  从 Chrome 同步 Suno Cookie（需要已登录 suno.com）")
auth_file = BACKEND / "suno_auth.json"
try:
    import browser_cookie3, json

    if not auth_file.exists():
        shutil.copy(BACKEND / "suno_auth.example.json", auth_file)

    jar  = browser_cookie3.chrome(domain_name=".suno.com")
    jar2 = browser_cookie3.chrome(domain_name="auth.suno.com")
    cookies = {c.name: c.value for c in jar  if not c.is_expired()}
    cookies.update({c.name: c.value for c in jar2 if not c.is_expired()})

    auth = json.loads(auth_file.read_text())
    if cookies.get("__session"): auth["session_token"] = cookies["__session"]
    if cookies.get("__client"):  auth["client_token"]  = cookies["__client"]
    if cookies.get("sessionid"): auth["sessionid"]     = cookies["sessionid"]
    auth["cookie_str"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    auth_file.write_text(json.dumps(auth, indent=2))
    print(f"  ✅ {len(cookies)} cookies 已同步到 backend/suno_auth.json")
except Exception as e:
    print(f"  ⚠️  Cookie 同步失败（{e}）")
    print("     请先在 Chrome 登录 https://suno.com，然后重新运行 setup.py")

# ─── 5. 初始化数据库 & seed data ─────────────────────────────
step("5/5  初始化数据库和演示账号")
db_file = BACKEND / "aegis_demo.db"
if db_file.exists():
    answer = input("  数据库已存在，重新初始化？(y/N) ").strip().lower()
    if answer == "y":
        db_file.unlink()
        print("  🗑  旧数据库已删除")
    else:
        print("  ⏭  保留现有数据库")

if not db_file.exists():
    run(f"{sys.executable} seed.py", cwd=BACKEND)

# ─── 完成 ─────────────────────────────────────────────────────
print(f"""
{'='*50}
  ✅  AEGIS Demo 安装完成！

  启动方式：
    双击 start-demo.sh
    或运行：bash {ROOT}/start-demo.sh

  账号：
    老师  teacher01 / aegis2026
    学生  stu01~stu30 / student123

  Suno 接入：
    默认 mock 模式（演示用，立即返回音频）
    如需真实生成：修改 backend/.env → SUNO_PROVIDER=browser
{'='*50}
""")
