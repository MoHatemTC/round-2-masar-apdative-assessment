CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id uuid references assessments(id) on delete cascade,
    candidate_email TEXT NOT NULL,
    status TEXT DEFAULT 'not-taken' CHECK (status IN ('not-taken', 'taken')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (assessment_id, candidate_email)
);
