# AEGIS 智慧音乐教室 Demo

## 快速启动

### 1. 后端
```bash
cd backend
cp .env.example .env          # 按需修改 SUNO_PROVIDER
pip install -r requirements.txt
python seed.py                # 初始化账号和演示数据（只需运行一次）
uvicorn main:app --reload
```

### 2. 前端
```bash
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173

## Demo 账号
| 角色 | 账号 | 密码 |
|------|------|------|
| 老师 | teacher01 | aegis2026 |
| 学生 | stu01~stu30 | student123 |

## Suno 接入
编辑 `backend/.env`：
- `SUNO_PROVIDER=mock`   — 本地测试，立即返回固定 MP3
- `SUNO_PROVIDER=goapi`  — 填入 GOAPI_KEY 使用真实 AI 生成
- `SUNO_PROVIDER=cookie` — 填入 SUNO_COOKIE 使用自己账号

## 项目结构
```
aegis-music-demo/
├── frontend/   Vue 3 + Vite + Wavesurfer.js
└── backend/    FastAPI + SQLite
```
