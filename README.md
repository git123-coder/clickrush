# ClickRush — 60-Second Click Challenge

A full-stack monorepo built for Team Shiksha evaluation.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Auth | JWT + bcrypt |

## Project Structure

```
clickrush/
├── frontend/         # React + Vite + TypeScript
├── backend/          # FastAPI + SQLAlchemy
├── .env.example      # Environment variable template
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node 18+
- PostgreSQL running locally

### 1. Clone & setup environment

```bash
cp .env.example .env
# Edit .env with your real values
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

API docs → http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App → http://localhost:5173

## Day 1 — What's Implemented

- ✅ PostgreSQL `users` table via Alembic migration
- ✅ `POST /api/auth/signup` — create account, hashed password
- ✅ `POST /api/auth/login` — returns JWT
- ✅ `GET /api/users/me` — protected endpoint, validates JWT
- ✅ React signup/login pages connected to backend
- ✅ Basic authenticated home screen + logout

## Day 2+ (Not Yet Implemented)

- 60-second click game
- Game sessions & score tracking
- Leaderboard
- Profile/history
- Deployment (Vercel + Render)
