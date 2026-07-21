ALTER TABLE answers
ADD CONSTRAINT uq_session_question UNIQUE (session_id, question_number);