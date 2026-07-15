-- 004_sessions_intake.sql — Intake Foundation (self-rating capture + starting prior support).
-- Additive only: every statement is safe to re-run and safe to run against a DB that already has
-- 001_init.sql applied (which already created `sessions.cv_json` / `sessions.intake_answers`).
-- Apply in the Supabase SQL editor, or via your migration runner, after 001..003.

-- 1. Guard the two columns the adaptive loop's init_session() reads from (session['intake_answers'],
--    session['cv_json']) — a no-op if 001_init.sql already created them, but this migration must not
--    assume that and must be able to stand alone.
alter table sessions add column if not exists intake_answers jsonb default '{}'::jsonb;
alter table sessions add column if not exists cv_json jsonb;

-- 2. When intake was submitted — lets the admin dashboard distinguish "created but not started"
--    from "self-rated, waiting on the adaptive loop", and gives us a timestamp for observability.
alter table sessions add column if not exists intake_submitted_at timestamptz;

-- 3. Normalized, queryable self-ratings: one row per (session, competency), explicitly keyed by
--    competency_id. sessions.intake_answers stays the source of truth the adaptive loop reads at
--    init (a single jsonb blob, cheap to load), while this table exists for admin review / audit /
--    joins ("show me every candidate who self-rated System Design a 5") without unpacking jsonb.
create table if not exists session_self_ratings (
  session_id     uuid not null references sessions(id) on delete cascade,
  competency_id  uuid not null references competencies(id) on delete cascade,
  self_rating    int  not null check (self_rating between 1 and 5),
  created_at     timestamptz default now(),
  updated_at     timestamptz default now(),
  primary key (session_id, competency_id)
);

create index if not exists idx_session_self_ratings_session
  on session_self_ratings(session_id);
