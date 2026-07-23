# Adaptive Competency Assessment — Intern Starter

A scoped starter for building a **question-bank-based adaptive competency assessment** — the same
flow as the Masar platform, trimmed to the essentials so you can build it end-to-end.

> Read `docs/ARCHITECTURE.md` (how the adaptive loop works) **before** writing code. This scaffold is
> deliberately made of small, commented stubs with `TODO`s — your job is to fill them in.

## The flow you're building (one sentence)
Admin uploads a JSON that defines competencies + questions → it becomes a **Question Set** → an
assessment is created from that set (competencies auto-derived) → a candidate self-rates each
competency 1–5 → an **adaptive loop** verifies the true level by asking a varied, personalized mix
of bank questions (generating extra open-ended ones if a competency's bank runs dry) until confident
→ a per-competency level + overall %/band report is produced.

## Layout
```
intern-starter/
├─ docs/ARCHITECTURE.md             # the adaptive engine explained (start here)
├─ data/sample_question_bank.json   # a ready 15-question AI-Engineer bank to import
├─ backend/                         # FastAPI + Supabase (Postgres)
│  ├─ requirements.txt
│  ├─ .env.example
│  ├─ migrations/001_init.sql       # the whole schema
│  └─ app/
│     ├─ main.py                    # app entrypoint
│     ├─ db.py                      # Supabase client
│     ├─ schemas/question_types.py  # per-type payload spec + validator (DONE — your reference)
│     ├─ services/question_bank.py  # select + personalize a question  (TODO)
│     ├─ services/grading.py        # grade an answer per type          (TODO)
│     ├─ agent/adaptive_loop.py     # the verification state machine    (TODO — the core)
│     └─ routes/{admin.py, chat.py} # import/create + one turn          (TODO)
└─ frontend/                        # Next.js (App Router)
   ├─ package.json
   ├─ lib/api.ts
   └─ app/admin/question-bank/page.tsx, app/assess/page.tsx
```

## Setup
### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # fill in SUPABASE_URL, SUPABASE_KEY, LLM key, RESEND key
# apply migrations/001_init.sql in your Supabase SQL editor
uvicorn app.main:app --reload --port 8000
```
### Frontend
```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

### Running everything with Docker (no local Python/Node install needed)
```bash
cp .env.example .env         # repo root — fill in SUPABASE_URL, SUPABASE_KEY, LLM_*, RESEND_*
docker compose up --build
```
- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- No Postgres container — the database is remote Supabase, reached via `SUPABASE_URL`/`SUPABASE_KEY`.
- Rebuilding after a code change: `docker compose down && docker compose up --build` (a plain
  `docker compose up` without `--build` reuses the old image and won't pick up new code).

## Suggested build order (each is a core deliverable)
1. **Schema** — apply `migrations/001_init.sql`.
2. **Question types** — read `schemas/question_types.py` (given); it's the contract for payloads.
3. **Import** — `routes/admin.py::import_bank`: upsert competencies + questions, validate, create a set.
4. **Selection + personalization** — `services/question_bank.py`.
5. **Grading** — `services/grading.py` (MCQ first, then rubric, then coding).
6. **The adaptive loop** — `agent/adaptive_loop.py` (init → ask → grade → estimate → converge → finalize).
7. **One turn** — `routes/chat.py::turn` wires the loop to HTTP.
8. **Scoring + report** — level→%/band, write `final_reports`.
9. **UI** — import page + candidate flow (incl. audio capture for voice questions).
10. **Email** — invite + report via Resend, with a send log (stub is a fine *interim* step, but real
    send + `email_logs` is the v1 target).

## Definition of done
Import `data/sample_question_bank.json` → create an assessment from the resulting set → take it as a
candidate → get a report with a per-competency level + overall %/band, drawing primarily from the bank
and generating open-ended questions if a competency's bank is exhausted before it converges (flagging
any low-confidence result), stopping early once confident, and emailing the report with a send log.