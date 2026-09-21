# PolicyPilot

PolicyPilot is an AI-powered banking policy and regulatory compliance platform.

## Technology Stack
- **Frontend**: Next.js (TypeScript, Tailwind CSS)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector (via Docker)
- **Environment Management**: uv for backend, npm for frontend

## Project Structure
```text
PolicyPilot/
├── frontend/         # Next.js application
├── backend/          # FastAPI application
├── infrastructure/   # Infrastructure setup (if any)
├── docs/             # Documentation
└── docker-compose.yml # Local database
```

## Setup & Local Development

### 1. Environment Setup
Copy the example environment file and adjust if necessary.
```bash
cp .env.example .env
cp .env.example frontend/.env.local
```

### 2. Database
Ensure Docker is installed and running.
```bash
docker compose up -d
```

### 3. Backend (FastAPI)
The backend uses `uv` for dependency management.
```bash
cd backend
uv venv
# On Windows: .venv\Scripts\activate
# On Unix: source .venv/bin/activate
uv pip install -r pyproject.toml
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend (Next.js)
The frontend uses `npm`.
```bash
cd frontend
npm install
npm run dev
```

## Health Checks
- Backend health API: `http://localhost:8000/health`
- Frontend app: `http://localhost:3000`

## Sequential Development
This project is developed sequentially through Modules 1 to 20, starting with the Foundation in Module 1.
