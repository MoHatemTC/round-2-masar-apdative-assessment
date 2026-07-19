CREATE TABLE IF NOT EXISTS invitations (
    id uuid primary key default gen_random_uuid(),
    assessment_id uuid references assessments(id) on delete cascade,
    candidate_email TEXT NOT NULL,
    status TEXT DEFAULT 'not-taken' CHECK (status IN ('not-taken', 'taken')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (assessment_id, candidate_email)
);
