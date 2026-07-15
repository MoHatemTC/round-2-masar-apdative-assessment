
create index if not exists idx_question_bank_competency_id
  on question_bank (competency_id);

create index if not exists idx_question_set_items_question_id
  on question_set_items (question_id);

alter table question_bank
  add column if not exists updated_at timestamptz default now();
