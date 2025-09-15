# LingoLens Reader

Production-ready scaffold for bilingual reading app using FastAPI + Next.js.

## Setup

1. **Install dependencies**
   ```bash
   cd backend && pip install -r requirements.txt
   cd ../frontend && npm install
   ```
2. **Environment**
   Copy `.env.example` to `.env` and fill in keys.
3. **Run dev servers**
   ```bash
   # Backend
   uvicorn app.main:app --reload
   # Frontend
   cd frontend && npm run dev
   # Celery worker
   celery -A app.services.pipeline.ingest worker -l info
   ```
4. **Tests**
   ```bash
   cd backend && pytest
   ```

## Database
Schema is defined in `db/schema.sql`. Use Supabase or Postgres to apply.

## Seed
Run `python backend/seed.py` after configuring env to insert demo data.
