-- ============================================================================
-- 005_reports.sql
-- Scoring, Reporting, Email & Observability Lane
--
-- Additive migration for:
--   • final_reports
--   • session_competency_results
--
-- Safe to re-run:
--   • Every CREATE uses IF NOT EXISTS.
--   • Every ALTER uses ADD COLUMN IF NOT EXISTS.
--   • Constraints are added through guarded DO blocks because PostgreSQL
--     does not support ADD CONSTRAINT IF NOT EXISTS.
--
-- Works for both:
--   • Fresh databases.
--   • Existing databases where these tables already exist.
--
-- Existing rows are safely backfilled before NOT NULL constraints are applied.
-- ============================================================================


-- ============================================================================
-- FINAL REPORTS
-- One row per completed session.
-- ============================================================================

CREATE TABLE IF NOT EXISTS final_reports (

    id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    session_id UUID UNIQUE
        REFERENCES sessions(id)
        ON DELETE CASCADE,

    overall_pct NUMERIC,

    overall_level INT,

    level_label TEXT,

    skill_scores JSONB
        DEFAULT '{}'::jsonb,

    has_low_confidence BOOLEAN
        DEFAULT FALSE,

    feedback TEXT,

    created_at TIMESTAMPTZ
        DEFAULT NOW()

);

-- --------------------------------------------------------------------------
-- Additive columns
-- --------------------------------------------------------------------------

ALTER TABLE final_reports
    ADD COLUMN IF NOT EXISTS has_low_confidence BOOLEAN DEFAULT FALSE;

ALTER TABLE final_reports
    ADD COLUMN IF NOT EXISTS skill_scores JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_final_reports_session_id
    ON final_reports (session_id);


-- ============================================================================
-- SESSION COMPETENCY RESULTS
-- One verified result for each (session, competency).
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_competency_results (

    session_id UUID
        REFERENCES sessions(id)
        ON DELETE CASCADE,

    competency_id UUID
        REFERENCES competencies(id),

    self_rating INT,

    initial_estimate INT,

    final_level INT,

    final_confidence NUMERIC,

    questions_asked INT,

    converged_reason TEXT,

    low_confidence BOOLEAN
        DEFAULT FALSE,

    created_at TIMESTAMPTZ
        DEFAULT NOW(),

    PRIMARY KEY (session_id, competency_id)

);

-- --------------------------------------------------------------------------
-- Additive columns
-- --------------------------------------------------------------------------

ALTER TABLE session_competency_results
    ADD COLUMN IF NOT EXISTS questions_asked INT;

ALTER TABLE session_competency_results
    ADD COLUMN IF NOT EXISTS low_confidence BOOLEAN DEFAULT FALSE;

ALTER TABLE session_competency_results
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_scr_session_id
    ON session_competency_results (session_id);

CREATE INDEX IF NOT EXISTS idx_scr_low_confidence
    ON session_competency_results (low_confidence)
    WHERE low_confidence = TRUE;


-- ============================================================================
-- SAFE BACKFILL
--
-- Existing rows may contain NULL values if these tables already existed.
-- Backfill them before applying NOT NULL constraints.
--
-- These columns intentionally remain nullable because they are populated only
-- when a competency has been finalized:
--
--   • final_level
--   • final_confidence
--   • questions_asked
--   • converged_reason
--   • self_rating
--   • initial_estimate
-- ============================================================================

UPDATE final_reports
SET has_low_confidence = FALSE
WHERE has_low_confidence IS NULL;

UPDATE final_reports
SET skill_scores = '{}'::jsonb
WHERE skill_scores IS NULL;

UPDATE final_reports
SET overall_pct = 0
WHERE overall_pct IS NULL;

UPDATE final_reports
SET overall_level = 1
WHERE overall_level IS NULL;

UPDATE final_reports
SET level_label = 'Novice'
WHERE level_label IS NULL;


ALTER TABLE final_reports
    ALTER COLUMN has_low_confidence SET NOT NULL;

ALTER TABLE final_reports
    ALTER COLUMN skill_scores SET NOT NULL;

ALTER TABLE final_reports
    ALTER COLUMN overall_pct SET NOT NULL;

ALTER TABLE final_reports
    ALTER COLUMN overall_level SET NOT NULL;

ALTER TABLE final_reports
    ALTER COLUMN level_label SET NOT NULL;


UPDATE session_competency_results
SET low_confidence = FALSE
WHERE low_confidence IS NULL;

ALTER TABLE session_competency_results
    ALTER COLUMN low_confidence SET NOT NULL;


-- ============================================================================
-- VALIDATION CONSTRAINTS
--
-- PostgreSQL does not support:
--      ADD CONSTRAINT IF NOT EXISTS
--
-- Therefore each constraint is added only if it does not already exist.
-- Constraint checks are scoped by both:
--      • conname
--      • conrelid
-- ============================================================================

DO
$$
BEGIN

    ------------------------------------------------------------------------
    -- final_reports
    ------------------------------------------------------------------------

    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_final_reports_overall_level'
          AND conrelid = 'final_reports'::regclass

    ) THEN

        ALTER TABLE final_reports
            ADD CONSTRAINT chk_final_reports_overall_level
            CHECK (overall_level BETWEEN 1 AND 5);

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_final_reports_overall_pct'
          AND conrelid = 'final_reports'::regclass

    ) THEN

        ALTER TABLE final_reports
            ADD CONSTRAINT chk_final_reports_overall_pct
            CHECK (overall_pct BETWEEN 0 AND 100);

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_final_reports_level_label'
          AND conrelid = 'final_reports'::regclass

    ) THEN

        ALTER TABLE final_reports
            ADD CONSTRAINT chk_final_reports_level_label
            CHECK (
                level_label IN (
                    'Novice',
                    'Developing',
                    'Proficient',
                    'Advanced',
                    'Expert'
                )
            );

    END IF;


    ------------------------------------------------------------------------
    -- session_competency_results
    ------------------------------------------------------------------------

    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_final_level'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_final_level
            CHECK (
                final_level IS NULL
                OR final_level BETWEEN 1 AND 5
            );

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_self_rating'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_self_rating
            CHECK (
                self_rating IS NULL
                OR self_rating BETWEEN 1 AND 5
            );

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_initial_estimate'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_initial_estimate
            CHECK (
                initial_estimate IS NULL
                OR initial_estimate BETWEEN 1 AND 5
            );

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_final_confidence'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_final_confidence
            CHECK (
                final_confidence IS NULL
                OR final_confidence BETWEEN 0 AND 1
            );

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_questions_asked'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_questions_asked
            CHECK (
                questions_asked IS NULL
                OR questions_asked >= 0
            );

    END IF;


    IF NOT EXISTS (

        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_scr_converged_reason'
          AND conrelid = 'session_competency_results'::regclass

    ) THEN

        ALTER TABLE session_competency_results
            ADD CONSTRAINT chk_scr_converged_reason
            CHECK (
                converged_reason IS NULL
                OR converged_reason IN (
                    'confidence',
                    'stable',
                    'max_questions'
                )
            );

    END IF;

END;
$$;