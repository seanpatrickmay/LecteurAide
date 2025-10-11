# LecteurAide

LecteurAide ingests French book PDFs, segments them into scenes with Google's Gemini models on Vertex AI, translates each sentence through Google Cloud Translation, extracts key vocabulary, and generates reading comprehension questions before presenting everything in a book-focused reader experience.

## Backend

### Requirements

- Python 3.11+
- Google Cloud project with the Translation API enabled
- Vertex AI access to Gemini models and a service account credential

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` inside `backend/`:

```
LECTEUR_GOOGLE_PROJECT_ID=your_project_id
LECTEUR_GOOGLE_LOCATION=global
LECTEUR_VERTEX_LOCATION=us-central1
LECTEUR_GOOGLE_CREDENTIALS_PATH=/absolute/path/service-account.json
LECTEUR_GEMINI_MODEL=gemini-1.5-pro
LECTEUR_DATABASE_URL=sqlite:///./lecteur_aide.db
CORS_ORIGINS=http://localhost:3000
```

`CORS_ORIGINS` accepts a comma-separated list when multiple origins are needed. Ensure the Google service account includes the `roles/cloudtranslate.user` and `roles/aiplatform.user` permissions.

### Run locally

```bash
uvicorn app.main:app --reload
```

### API highlights

- `POST /books/upload` (multipart with `file`, `title`) — ingest a PDF. Streams server-sent progress events while chunks are processed and finishes with the created `book_id`.
- `GET /books` — list processed books with scene counts.
- `GET /books/{book_id}` — retrieve a book with ordered scenes, sentences, vocabulary, and comprehension questions.

The backend persists data to SQLite (`backend/lecteur_aide.db` by default). Switch `LECTEUR_DATABASE_URL` to use PostgreSQL or any SQLAlchemy-supported database.

## Frontend

### Requirements

- Node.js 18+
- Yarn or npm

### Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local` with:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

### Application pages

1. **Upload (`/`)** — submit a French PDF with a title for processing.
2. **Library (`/library`)** — browse ingested books and jump into the reader.
3. **Book viewer (`/books/[bookId]`)** — read one scene at a time in a paper-inspired layout, advance through scenes, click sentences to reveal translations, review highlighted vocabulary, and study scene-specific comprehension questions.

Run both services together to experience the full pipeline: upload a book via the frontend, let backend processing complete, and explore the rendered scenes in the viewer.
