-- ============================================================================
-- 008_performance_indexes.sql
--
-- Adds missing indexes on foreign-key columns used in WHERE, JOIN, and ORDER BY
-- clauses across the admin dashboard, invitation, and reporting endpoints.
--
-- Uses CREATE INDEX CONCURRENTLY so we do NOT acquire an exclusive table lock
-- in production. Safe to re-run (IF NOT EXISTS).
--
-- NOTE: CONCURRENTLY cannot run inside a transaction block. If your migration
-- runner wraps each file in BEGIN/COMMIT, run these statements manually in the
-- Supabase SQL editor instead.
-- ============================================================================

-- sessions: filtered by assessment_id in list_sessions, list_invitations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_assessment_id
  ON sessions(assessment_id);

-- sessions: joined by candidate_email in list_invitations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_candidate_email
  ON sessions(candidate_email);

-- sessions: ORDER BY created_at DESC on every admin listing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_created_at_desc
  ON sessions(created_at DESC);

-- invitations: filtered by assessment_id in list_invitations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invitations_assessment_id
  ON invitations(assessment_id);

-- invitations: filtered by candidate_email in create_invitation dedup check
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invitations_candidate_email
  ON invitations(candidate_email);

-- answers: filtered by session_id in report queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_answers_session_id
  ON answers(session_id);
