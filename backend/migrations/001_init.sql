-- 001_init.sql — full schema for the adaptive competency assessment.
-- Apply in the Supabase SQL editor. Additive + safe to re-run.

-- Competency tree: track (top level) → sub-competencies (children).
create table if not exists competencies (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null check (kind in ('track','sub')),
  code        text unique not null,
  name        text not null,
  domain      text default 'technical',
  parent_id   uuid references competencies(id) on delete cascade,
  sort_order  int default 0,
  is_active   boolean default true,
  created_at  timestamptz default now()
);

-- The question bank. payload shape depends on tool_type (see schemas/question_types.py).
create table if not exists question_bank (
  id            uuid primary key default gen_random_uuid(),
  source_ref    text unique,                         -- idempotent import key
  competency_id uuid references competencies(id) on delete cascade,
  tool_type     text not null,                       -- mcq | voice | coding | visualization | ...
  difficulty    text,                                -- easy | medium | hard (metadata)
  body          text not null,
  rubric        text,
  payload       jsonb default '{}'::jsonb,
  tags          text[] default '{}',
  is_active     boolean default true,
  created_at    timestamptz default now()
);

-- Reusable groups of bank questions. An upload becomes one set.
create table if not exists question_sets (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  description text,
  created_at  timestamptz default now()
);
create table if not exists question_set_items (
  set_id      uuid references question_sets(id) on delete cascade,
  question_id uuid references question_bank(id) on delete cascade,
  sort_order  int default 0,
  primary key (set_id, question_id)
);

-- An assessment = a set + the competencies it measures (derived from the set).
create table if not exists assessments (
  id              uuid primary key default gen_random_uuid(),
  title           text not null,
  question_set_id uuid references question_sets(id),
  competency_ids  uuid[] default '{}',
  time_limit_min  int default 30,
  is_published    boolean default false,
  share_token     text unique,
  created_at      timestamptz default now()
);

-- A candidate taking an assessment. agent_state holds the loop's serialized state.
create table if not exists sessions (
  id             uuid primary key default gen_random_uuid(),
  assessment_id  uuid references assessments(id) on delete set null,
  candidate_name text,
  candidate_email text,
  cv_json        jsonb,                              -- parsed CV (optional)
  intake_answers jsonb default '{}'::jsonb,          -- self-ratings live here
  agent_state    jsonb default '{}'::jsonb,          -- <- the adaptive loop round-trips this
  status         text default 'identity',            -- identity | in_progress | completed
  started_at     timestamptz,
  completed_at   timestamptz,
  created_at     timestamptz default now()
);

-- One row per graded answer. Persists what was ASKED (question_id/body, null id for generated
-- fallback questions) and what was answered, per the "persist each served question" requirement.
create table if not exists answers (
  id               uuid primary key default gen_random_uuid(),
  session_id       uuid references sessions(id) on delete cascade,
  question_number  int,
  question_id      uuid references question_bank(id) on delete set null,  -- null = generated fallback, or its bank question was later deleted
  question_body    text,                              -- the (personalized) question as served
  competency_id    uuid,
  tool_type        text,
  score            numeric,                           -- 0..5
  rationale        text,
  answer_text      text,
  created_at       timestamptz default now(),
  unique (session_id, question_number)               -- resume guard: no double-count
);

-- The final report.
create table if not exists final_reports (
  id            uuid primary key default gen_random_uuid(),
  session_id    uuid unique references sessions(id) on delete cascade,
  overall_pct   numeric,
  overall_level int,
  level_label   text,
  skill_scores  jsonb default '{}'::jsonb,            -- {competency: {level, pct, label, low_confidence}}
  feedback      text,
  created_at    timestamptz default now()
);

-- Per-competency verification result (self-rating vs verified).
create table if not exists session_competency_results (
  session_id       uuid references sessions(id) on delete cascade,
  competency_id    uuid references competencies(id),
  self_rating      int,
  initial_estimate int,                               -- from the CV
  final_level      int,
  final_confidence numeric,
  converged_reason text,
  primary key (session_id, competency_id)
);

-- Audit: every LLM call + grade (non-functional requirement).
-- NOTE: `estimate` is a deterministic Bayesian update (no LLM) — logging it is optional.
create table if not exists ai_logs (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid,
  kind       text,                                    -- personalize | grade | cv_estimate | stt | generate
  prompt     text,
  response   text,
  created_at timestamptz default now()
);

-- Voice questions capture audio → transcript before rubric grading (additive).
alter table answers add column if not exists audio_url   text;
alter table answers add column if not exists transcript  text;

-- Email send log: invite + report deliveries (deliverable: "email with send logs").
create table if not exists email_logs (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete set null,
  kind       text,                                    -- invite | report | admin_notify
  recipient  text,
  subject    text,
  status     text default 'queued',                   -- queued | sent | failed
  provider_id text,                                   -- Resend message id
  error      text,
  created_at timestamptz default now()
);

-- Invitations Table
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id),
    candidate_email TEXT NOT NULL,
    status TEXT DEFAULT 'not-taken' CHECK (status IN ('not-taken', 'taken')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);