-- 006_proctoring.sql — AI Proctoring: consent, captured media, batch idempotency.
-- Additive only, safe to re-run.

-- 1. Session-level consent state --------------------------------------------
alter table sessions add column if not exists proctoring_consent      boolean;
alter table sessions add column if not exists proctoring_consent_at   timestamptz;
alter table sessions add column if not exists proctoring_status       text;
--   'active' when the candidate agreed and a reference photo was uploaded,
--   'proctoring_unavailable' when the candidate declined,
--   null when we haven't asked yet.

-- 2. Captured media (reference + Q&A frames) --------------------------------
create table if not exists proctoring_captures (
  id               uuid primary key default gen_random_uuid(),
  session_id       uuid not null references sessions(id) on delete cascade,
  question_number  int,                                      -- null on the reference photo
  kind             text not null check (kind in ('reference','frame')),
  storage_path     text not null,                            -- inside the private 'proctoring' bucket
  analysis         jsonb,                                    -- structured verdict from the vision worker
  analysis_status  text not null default 'pending'
                   check (analysis_status in ('pending','done','failed')),
  created_at       timestamptz default now()
);

create index if not exists idx_proctoring_captures_session
  on proctoring_captures(session_id, created_at);

create index if not exists idx_proctoring_captures_pending
  on proctoring_captures(analysis_status)
  where analysis_status = 'pending';

-- Exactly one 'reference' capture per session.
create unique index if not exists uq_proctoring_captures_reference
  on proctoring_captures(session_id)
  where kind = 'reference';

-- 3. Batch idempotency ledger -----------------------------------------------
-- The frontend attaches a client-generated batch_id to every upload; a retry
-- (network hiccup) with the same id must not double-insert captures.
create table if not exists proctoring_batches (
  batch_id     text primary key,
  session_id   uuid not null references sessions(id) on delete cascade,
  frame_count  int  not null,
  created_at   timestamptz default now()
);

-- 4. RLS ---------------------------------------------------------------------
-- Media is PII. Access flows through the FastAPI backend (service role); no
-- permissive policies are added, so direct-from-client reads/writes are denied.
alter table proctoring_captures enable row level security;
alter table proctoring_batches   enable row level security;

-- 5. Manual step (Supabase Dashboard):
--    Storage > New bucket:
--      Name:   proctoring
--      Public: OFF
--    Objects will be laid out as:
--      {session_id}/reference.jpg
--      {session_id}/frames/{timestamp_ms}.jpg
