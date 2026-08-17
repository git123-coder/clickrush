# ClickRush

ClickRush is a full-stack, server-authoritative web application where users compete to achieve the highest number of clicks in a 60-second window.

## Technology Stack
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Backend**: FastAPI + Python (SQLAlchemy)
- **Database**: PostgreSQL
- **Migrations**: Alembic

---

## Prerequisites
To run the project locally, you will need:
- Python 3.11+
- Node.js 18+
- PostgreSQL database

---

## Local Setup and Run Instructions

### 1. Repository setup
Clone the repository and enter the directory:
```bash
git clone <repository_url>
cd clickrush
```

### 2. Environment variables
The backend requires environment variables to connect to the database and sign JWT tokens.

Copy the `.env.example` file to create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Ensure the `.env` file contains the required variables:
- `DATABASE_URL`: PostgreSQL connection string for your local PostgreSQL database (e.g. `postgresql+psycopg2://postgres:yourpassword@localhost:5432/clickrush`).
- `JWT_SECRET_KEY`: A strong secret key for JWT token signing.
- `JWT_ALGORITHM`: Algorithm to use (e.g. `HS256`).
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time in minutes (e.g. `60`).
- `FRONTEND_URL`: URL of the local React dev server (e.g. `http://localhost:5173`).

### 3. Backend setup
Open a new terminal to set up and run the backend:
```bash
# Create the local PostgreSQL database
createdb clickrush

cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload
```
The FastAPI backend will run on `http://127.0.0.1:8000`.

### 4. Frontend setup
Open another terminal to set up and run the frontend:
```bash
cd frontend
npm install
npm run dev
```
The application will be accessible at `http://localhost:5173`. Both the frontend and backend must be running simultaneously.

---

## Database Schema

The database uses PostgreSQL, and the schema is managed by Alembic.

### `users`
Stores authenticated users.
- **Columns**: `id` (UUID, Primary Key), `username` (Unique, Indexed), `email` (Unique, Indexed), `password_hash`, `created_at`.
- **Relationships**: Has many `game_sessions` and many `scores`.

### `game_sessions`
Represents a user's 60-second game attempt. Server-authoritative timestamps prevent cheating.
- **Columns**: `id` (UUID, Primary Key), `user_id` (Foreign Key), `started_at`, `expires_at`, `finished_at`, `status` (Enum: `active`, `completed`, `expired`).
- **Relationships**: Belongs to `users`. Has one `scores`.
- **Important Rule**: A partial unique index (`uq_one_active_session_per_user` on `user_id` where `status = 'active'`) prevents a single user from having multiple active game sessions simultaneously.

### `scores`
Stores the final validated score of a completed game session.
- **Columns**: `id` (UUID, Primary Key), `game_session_id` (Foreign Key), `user_id` (Foreign Key), `clicks` (Integer), `created_at`.
- **Unique Constraints**: `uq_scores_game_session_id` guarantees exactly one score per game session.
- **Relationships**: Belongs to `users` and `game_sessions`.

---

## API Endpoints

### Authentication & Users
| Method | Endpoint | Purpose | Auth |
| ------ | -------- | ------- | ---- |
| `POST` | `/api/auth/signup` | Create a new user account | No |
| `POST` | `/api/auth/login` | Login and receive a JWT token | No |
| `GET` | `/api/users/me` | Retrieve the authenticated user's profile | Yes |
| `GET` | `/api/users/me/games` | Paginated list of a user's game history (params: `limit`, `offset`) | Yes |
| `GET` | `/api/users/me/rankings` | The user's exact Global, Daily, and Weekly rankings | Yes |

### Games
| Method | Endpoint | Purpose | Auth |
| ------ | -------- | ------- | ---- |
| `POST` | `/api/games/start` | Start a new 60-second game session | Yes |
| `POST` | `/api/games/{game_id}/finish` | Finalize a game session and submit clicks | Yes |

### Leaderboards
| Method | Endpoint | Purpose | Auth |
| ------ | -------- | ------- | ---- |
| `GET` | `/api/leaderboards/global` | Top scores all-time (params: `limit`) | No |
| `GET` | `/api/leaderboards/daily` | Top scores today (params: `limit`) | No |
| `GET` | `/api/leaderboards/weekly` | Top scores in the last 7 days (params: `limit`) | No |

---

## API Documentation

Once the backend is running locally, the interactive Swagger/OpenAPI documentation is available at:
`http://127.0.0.1:8000/docs`

---

## Deployed Application

Live URL: https://clickrush-pi.vercel.app/

> **Note:** The backend may take 30–60 seconds to respond on the first request after a period of inactivity due to cold starts. Subsequent requests will be fast.