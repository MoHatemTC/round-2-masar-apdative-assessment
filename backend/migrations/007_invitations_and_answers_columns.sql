-- ============================================================================
-- 007_invitations_and_answers_columns.sql
--
-- Missing migrations were breaking three things:
--   • invitations.token   — admin.py writes a "token" field on every
--                           invitation insert; the column never existed, so
--                           creating an invitation fails outright.
--   • answers.flagged     — voice-answer writes fail on a fresh DB without it.
--   • answers.skipped     — same.
--
-- Also sets is_published = true on existing assessments as a one-time
-- backfill — see the companion code fix in create_assessment (admin.py),
-- which now sets is_published = true at creation time. Without either half
-- of this fix, assessments.is_published defaults to false and every
-- candidate link 404s at candidate_intake.py's is_published check.
--
-- Safe to re-run: every ALTER uses ADD COLUMN IF NOT EXISTS.
-- ============================================================================

ALTER TABLE invitations
    ADD COLUMN IF NOT EXISTS token TEXT;

UPDATE invitations
SET token = gen_random_uuid()::text
WHERE token IS NULL;

ALTER TABLE invitations
    ALTER COLUMN token SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'invitations_token_key'
    ) THEN
        ALTER TABLE invitations ADD CONSTRAINT invitations_token_key UNIQUE (token);
    END IF;
END $$;

ALTER TABLE answers
    ADD COLUMN IF NOT EXISTS flagged BOOLEAN DEFAULT FALSE;

ALTER TABLE answers
    ADD COLUMN IF NOT EXISTS skipped BOOLEAN DEFAULT FALSE;

UPDATE answers SET flagged = FALSE WHERE flagged IS NULL;
UPDATE answers SET skipped = FALSE WHERE skipped IS NULL;

ALTER TABLE answers ALTER COLUMN flagged SET NOT NULL;
ALTER TABLE answers ALTER COLUMN skipped SET NOT NULL;

UPDATE assessments
SET is_published = TRUE
WHERE is_published IS FALSE;
