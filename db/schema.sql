create table books (
  id uuid primary key,
  title text,
  author text,
  language_code text,
  description text,
  cover_url text,
  is_public boolean default true,
  created_at timestamptz default now()
);

create table scenes (
  id uuid primary key,
  book_id uuid references books(id),
  scene_index int,
  title text,
  raw_text text,
  created_at timestamptz default now()
);

create table sentences (
  id uuid primary key,
  scene_id uuid references scenes(id),
  sentence_index int,
  source_text text,
  translation_en text,
  quality_flags jsonb,
  created_at timestamptz default now()
);

create table scene_exercises (
  id uuid primary key,
  scene_id uuid references scenes(id),
  vocab jsonb,
  questions jsonb,
  answers jsonb,
  created_at timestamptz default now(),
  reviewed_by text,
  reviewed_at timestamptz
);

create table user_progress (
  user_id uuid,
  book_id uuid,
  last_scene_index int,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (user_id, book_id)
);

create table ingestion_jobs (
  id uuid primary key,
  book_id uuid,
  status text,
  steps jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  error text
);
