-- 002_bank.sql — additive changes supporting the Bank Ingestion & Validation lane.
--
-- DEPENDENCY: this migration does NOT create competencies, question_bank, question_sets,
-- or question_set_items — all four already exist, created by 001_init.sql, which must be
-- applied first. Confirmed by running 001_init.sql against a live Supabase project and
-- verifying all four tables before applying this file. 002_bank.sql only adds indexes and
-- one column on top of that existing baseline.
--
-- Applies on top of 001_init.sql. Additive only: no drops, no renames, no destructive
-- alterations of existing columns. Safe to re-run (every statement is idempotent).

-- competencies.parent_id is a foreign key (a 'sub' competency pointing back to its parent
-- 'track') but foreign keys are NOT auto-indexed by Postgres (unlike primary keys). Finding
-- all children of a track is a plausible lookup, so index it.
create index if not exists idx_competencies_parent_id
  on competencies (parent_id);

-- question_bank.competency_id is a foreign key but foreign keys are NOT auto-indexed
-- by Postgres (unlike primary keys). The import/validation flow will repeatedly ask
-- "which questions belong to competency X" once upsert lands, so index it now.
create index if not exists idx_question_bank_competency_id
  on question_bank (competency_id);

-- question_set_items has a composite primary key (set_id, question_id), which only
-- accelerates lookups that start with set_id. Looking up "which sets contain this
-- question" (by question_id alone) gets no benefit from that composite key, so add
-- a dedicated index for the reverse direction.
create index if not exists idx_question_set_items_question_id
  on question_set_items (question_id);

-- question_sets has no foreign key columns of its own (id, name, description only), so
-- there is nothing on it to index in this migration.

-- question_bank currently has created_at but no updated_at. Next week's upsert step
-- ("upsert questions on source_ref, preserve difficulty") needs a way to distinguish
-- "freshly re-imported" from "untouched since creation." Add it now, defaulted so
-- existing rows are unaffected, so the upsert work doesn't require its own migration.
alter table question_bank
  add column if not exists updated_at timestamptz default now();