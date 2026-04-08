# PROJECT MAP — AEGIS 智慧音乐教室 Demo

> 此文件供 AI 助手参考，避免创建重复文件或写错路径。
> 修改文件前先对照此 map 确认正确路径。
> 
> 项目根目录：`~/Desktop/aegis-music-demo/`
> GitHub：https://github.com/xiezijia/aegis-music-demo
> 运行端口：后端 :8000 | 前端 :5173

---

## 一、目录树

```
aegis-music-demo/
├── start-demo.sh              # 一键启动（同步 cookie + 启动前后端 + 打开浏览器）
├── setup.py                   # 首次安装（pip + npm + cookie 同步 + seed DB）
├── README.md
├── .gitignore
│
├── backend/                   ← FastAPI + SQLite，运行在 :8000
│   ├── main.py                # FastAPI 入口，lifespan 启动 keep-alive task
│   ├── database.py            # SQLite init，get_db() 依赖注入，DB_PATH 变量
│   ├── models.py              # Pydantic 模型（LoginRequest, GenerateRequest, TrackOut...）
│   ├── seed.py                # 初始化 31 个账号 + 3 个学生的演示作品
│   ├── requirements.txt       # Python 依赖
│   ├── .env                   # ⚠️ 不提交 git（含密钥）
│   ├── .env.example           # 环境变量模板
│   ├── suno_auth.json         # ⚠️ 不提交 git（含 Suno cookie/JWT）
│   ├── suno_auth.example.json # JSON 结构模板
│   ├── aegis_demo.db          # ⚠️ SQLite 数据库（不提交 git）
│   │
│   ├── routers/               # FastAPI 路由（prefix 已含 /api/）
│   │   ├── __init__.py
│   │   ├── auth.py            # POST /api/auth/login, GET /api/auth/me
│   │   ├── music.py           # POST /api/music/generate
│   │   │                      # GET  /api/music/status/{track_id}
│   │   │                      # GET  /api/music/my-tracks
│   │   │                      # POST /api/music/submit/{track_id}
│   │   └── teacher.py         # GET  /api/teacher/submissions
│   │                          # GET  /api/teacher/students
│   │                          # GET  /api/teacher/student/{id}/tracks
│   │                          # POST /api/teacher/feedback
│   │
│   └── services/
│       ├── __init__.py
│       └── suno.py            # ★ Suno 核心模块（见下方详解）
│
├── frontend/                  ← Vue 3 + Vite，运行在 :5173
│   ├── index.html             # HTML 入口，挂载 #app
│   ├── vite.config.js         # 代理：/api → http://localhost:8000
│   ├── package.json           # 依赖：vue vue-router pinia axios wavesurfer.js
│   │
│   └── src/
│       ├── main.js            # createApp + Pinia + Router + style.css
│       ├── App.vue            # 根组件（Navbar + RouterView + Toast）
│       │
│       ├── assets/
│       │   └── style.css      # 全局 AEGIS 深色主题（CSS 变量 --gold, --navy 等）
│       │
│       ├── router/
│       │   └── index.js       # 路由：/login /studio /history /teacher
│       │                      # 守卫：未登录→/login，角色错误→对应首页
│       │
│       ├── stores/
│       │   ├── auth.js        # useAuthStore：token/role/displayName/userId
│       │   │                  # 方法：login(username,password) / logout()
│       │   └── music.js       # useMusicStore：tracks[]
│       │                      # 方法：fetchMyTracks() / generate(payload) / pollStatus(id) / submitTrack(id)
│       │
│       ├── views/
│       │   ├── Login.vue      # 登录页（含动态波形背景 + demo 账号一键填入）
│       │   ├── Studio.vue     # 学生作曲工坊（左：表单 | 右：结果+历史）
│       │   ├── History.vue    # 学生作品版本树（按 parent_id 分组）
│       │   └── Teacher.vue    # 教师仪表盘（左：学生列表 | 中：作品+评语 | 右：统计）
│       │
│       └── components/
│           ├── Navbar.vue     # 顶部导航（品牌 + 路由链接 + 用户信息 + 退出）
│           ├── WavePlayer.vue # Wavesurfer.js 封装（props: url）
│           └── TrackCard.vue  # 作品卡片（props: track）slot: actions
│
└── docs/
    ├── AEGIS智慧音乐教室方案.html  # 9页 HTML 演示文稿（给学校老师汇报用）
    ├── 逆向工程WebAPI思考笔记.md   # 方法论：思路+原理
    └── 逆向工程WebAPI操作日志.md   # 操作日志：命令+报错+修复过程
```

---

## 二、核心模块详解

### `backend/services/suno.py` ★

**对外接口（其他文件应使用的）：**
```python
from services.suno import generate_music, init_keep_alive, get_token, suno_cookie

# 生成音乐（在 FastAPI 路由里调用）
result = await generate_music(prompt, style, lyrics)
# 返回: {"audio_url": str, "task_id": str, "title": str, "image_url": str}

# 在 main.py lifespan 里初始化
init_keep_alive()   # 启动 asyncio 后台任务，5 秒刷新 JWT
get_token()         # 读当前 JWT 字符串
suno_cookie.load_from_file()  # 从 suno_auth.json 加载 cookie
```

**`SUNO_PROVIDER` 环境变量（在 backend/.env 配置）：**
| 值 | 行为 |
|---|---|
| `mock` | 立即返回固定 MP3（演示/开发，不消耗 API） |
| `browser` | Android UA + curl_cffi + Keep-Alive（需 suno_auth.json） |
| `goapi` | GoAPI 商业代理（需 GOAPI_KEY 环境变量） |

**Keep-Alive 机制：**
- `init_keep_alive()` 在 `main.py` lifespan 里调用
- asyncio 后台任务每 5 秒调 `clerk.suno.com/v1/client/sessions/{sid}/tokens`
- token 存在内存变量 `_token` 并写回 `suno_auth.json`
- 使用 `curl_cffi.requests.AsyncSession(impersonate="edge101")` 避免 libcurl/asyncio 冲突

**suno_auth.json 字段：**
```json
{
  "sessionid":     "Django session ID（studio-api 旧域名）",
  "session_token": "Clerk JWT（__session cookie 值）",
  "client_token":  "Clerk 刷新令牌（__client cookie 值）",
  "cookie_str":    "完整 cookie 字符串（由 browser_cookie3 自动填充）"
}
```

---

### `backend/database.py`

```python
DB_PATH = os.getenv("DATABASE_URL", "./aegis_demo.db")  # 相对于 CWD（backend/）

# 三张表
users     # id, username, display_name, hashed_password, role(student|teacher)
tracks    # id, user_id, title, prompt, style, lyrics, audio_url, status, version, parent_id, submitted
feedbacks # id, track_id, teacher_id, comment, score
```

---

### `backend/routers/auth.py`

```python
# JWT 配置
SECRET_KEY   = os.getenv("SECRET_KEY")
ALGORITHM    = "HS256"
EXPIRE_MIN   = ACCESS_TOKEN_EXPIRE_MINUTES

# 核心依赖（其他 router 用）
async def current_user(creds=Depends(bearer), db=Depends(get_db)) -> dict
```

---

## 三、API 接口速查

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/auth/login` | 无 | 返回 JWT token + role |
| GET  | `/api/auth/me` | 登录 | 返回当前用户信息 |
| POST | `/api/music/generate` | student | 提交生成，后台异步跑 |
| GET  | `/api/music/status/{id}` | student | 轮询生成状态 |
| GET  | `/api/music/my-tracks` | student | 我的所有作品 |
| POST | `/api/music/submit/{id}` | student | 提交给老师 |
| GET  | `/api/teacher/submissions` | teacher | 所有已提交作品 |
| GET  | `/api/teacher/students` | teacher | 学生列表+统计 |
| GET  | `/api/teacher/student/{id}/tracks` | teacher | 某学生所有版本 |
| POST | `/api/teacher/feedback` | teacher | 发送评语 |

---

## 四、前端路由规则

| 路径 | 组件 | 角色 | 说明 |
|------|------|------|------|
| `/login` | Login.vue | 所有 | 登录页 |
| `/studio` | Studio.vue | student | 作曲工坊 |
| `/history` | History.vue | student | 版本历史 |
| `/teacher` | Teacher.vue | teacher | 批改仪表盘 |
| `/` | → `/login` | — | 重定向 |

---

## 五、演示账号

| 角色 | 账号 | 密码 |
|------|------|------|
| 老师 | `teacher01` | `aegis2026` |
| 学生 | `stu01`~`stu30` | `student123` |

前 3 个学生（stu01~stu03）有预置的演示作品和版本历史。
stu01 还有老师评语，分数 88。

---

## 六、启动命令

```bash
# 首次安装
python3 setup.py

# 日常启动
bash start-demo.sh

# 手动启动（调试时）
cd backend && uvicorn main:app --port 8000 --reload
cd frontend && npm run dev

# 同步 Chrome Cookie（token 过期时）
python3 -c "
import browser_cookie3, json
from pathlib import Path
jar = browser_cookie3.chrome(domain_name='.suno.com')
cookies = {c.name:c.value for c in jar if not c.is_expired()}
auth = json.loads(Path('backend/suno_auth.json').read_text())
if cookies.get('__client'): auth['client_token'] = cookies['__client']
auth['cookie_str'] = '; '.join(f"{k}={v}" for k,v in cookies.items())
Path('backend/suno_auth.json').write_text(json.dumps(auth, indent=2))
"

# 重新初始化演示数据
cd backend && python3 seed.py
```

---

## 七、新增功能时的注意事项

**新增后端 API：**
1. 在 `backend/routers/` 下的对应文件添加路由
2. 如需新数据表：在 `backend/database.py` 的 `CREATE_TABLES` 字符串里加 SQL
3. 在 `backend/models.py` 添加对应 Pydantic 模型

**新增前端页面：**
1. 在 `frontend/src/views/` 创建新 Vue 文件
2. 在 `frontend/src/router/index.js` 添加路由记录
3. 在 `frontend/src/components/Navbar.vue` 添加导航链接（如需要）

**修改 Suno 生成逻辑：**
- 只改 `backend/services/suno.py`
- 对外接口 `generate_music(prompt, style, lyrics)` 签名不要变
- `init_keep_alive()` 和 `get_token()` 供 main.py 使用

**修改主题颜色：**
- 只改 `frontend/src/assets/style.css` 里的 CSS 变量（`:root` 块）
