# Architecture — the adaptive competency engine

This is the mental model to build. Keep it simple; the cleverness is in the loop, not the framework.

## Data model (see `backend/migrations/001_init.sql`)
- **competencies** — a tree: `kind='track'` (top level) with `kind='sub'` children (`parent_id`). Unique `code`.
- **question_bank** — one row per question: `competency_id` (usually a sub), `tool_type`, `difficulty`,
  `body`, `payload` (jsonb, shape depends on `tool_type`), unique `source_ref`.
- **question_sets** / **question_set_items** — a reusable group of bank questions (an *upload* becomes one set).
- **assessments** — `question_set_id` + the derived `competency_ids` it measures + `time_limit`.
- **sessions** — a candidate taking an assessment; holds `agent_state` (jsonb) that the loop round-trips.
- **answers** — one row per graded question (score 0–5 + rationale).
- **final_reports** — per-competency level + overall %/band.

## The key idea
For each competency the assessment measures, form an **initial belief** about the candidate's 1–5 level
(the CV estimate blended 50/50 with their self-rating), then **probe with questions until confident**,
then stop. Not a fixed quiz — as few or as many questions as needed per competency.

The belief is a **Bayesian posterior** over the levels `{1,2,3,4,5}`: start peaked on the prior, and after
each graded answer multiply by a likelihood (score × question difficulty) and renormalize. `level =
argmax(posterior)`; `confidence = 1 − normalized_spread(posterior)`. The update is deterministic — **no LLM
call** — so it's cheap, reproducible, and debuggable. The self-rating and CV enter only through the prior.

## The loop (a small state machine, one question per HTTP turn)
Run the graph once per `POST /chat/turn`. Persist all state in `sessions.agent_state` and reload it next
turn (stateless server, resumable client).

```
              ┌─────────────┐
  turn 0 ───▶ │ init_session│  load competencies, self-ratings, CV estimate → starting prior
              └─────┬───────┘
                    ▼
              ┌─────────────┐   pick next un-converged competency → select a bank question at a
              │ pick_question│  difficulty targeting the current estimate, varied by tool type
              └─────┬───────┘  → personalize it → strip answer key → SEND to browser, end turn
   (answer)         ▼
              ┌─────────────┐   grade the answer (0–5) per tool_type
              │    grade     │
              └─────┬───────┘
                    ▼
              ┌─────────────┐   Bayesian update of the 1–5 posterior → level + confidence
              │   estimate   │   (deterministic, no LLM; prior carries the self-rating/CV)
              └─────┬───────┘
                    ▼
              ┌───────────────┐ converged? confidence ≥ 0.90  OR  level stable 3×  OR  asked 10
              │check_convergence│ yes → mark done, move to next competency
              └─────┬─────────┘
                    ▼  (loop back to pick_question; when all converged →)
              ┌─────────────┐   level→%/band, write final_report, email
              │   finalize   │
              └─────────────┘
```

## Why questions feel personalized (three layers)
1. **Start on the candidate.** Read the CV → per-competency estimate; blend 50/50 with their self-rating
   (`prior = round(0.5·CV + 0.5·self)`; self-rating alone when there's no CV; default 3 when neither
   exists) so the loop opens near where they actually are.
2. **Rewrite each question to them.** Before asking, an LLM rewrites the bank question **and** its MCQ
   options to reference the candidate's background — **without changing what's tested**. The server
   re-injects the original answer key afterward, so **the correct answer is invariant** and the measured
   competency stays deterministic.
3. **Adapt difficulty to them.** Each question targets the current level estimate, so a strong candidate
   climbs into harder questions and a struggling one is met where they are. The bank stores difficulty as
   `easy|medium|hard`; the loop works on the 1–5 level scale, so map through
   `schemas/question_types.py::level_of` (`easy=2, medium=3, hard=4`) when selecting and estimating.

## Grading (per `tool_type`)
- **mcq** → exact match on `payload.answer_key.correct_id`.
- **coding** → run against `payload.test_cases` in a **sandbox** (`score = 5 × passed/total`), **plus** an
  LLM judge on approach/quality for partial credit.
- **voice** → capture audio in the browser → **STT transcript** → LLM scores against the rubric.
- **open-ended / visualization** → LLM scores the answer against `payload.evaluation_criteria` / `expected_insights`.
- Always return a **0–5** score + a short rationale.

## Scoring
- Per competency: verified 1–5 level.
- `pct = level × 20`; bands: 0–20 Novice · 21–40 Developing · 41–60 Proficient · 61–80 Advanced · 81–100 Expert.
- Overall % = average level × 20.

## Convergence knobs (tune, but start here — keep these consistent across the docs)
- `CONFIDENCE_TARGET = 0.90`
- `MAX_QUESTIONS = 10` per competency
- `STABLE_WINDOW = 3` (same level 3 estimates in a row → done)
- Confidence ceiling by question count `{1:0.5, 2:0.7, 3:0.85}` else `0.97` — so one answer can't trigger the stop; it must probe ~4+.

## Bank exhaustion
If a competency's bank runs dry before it converges, **keep generating open-ended questions** (never MCQ — an
invented answer key can't be trusted) and keep probing until it converges or hits `MAX_QUESTIONS`. Always
record a final level; if it stopped only by hitting the cap below `CONFIDENCE_TARGET`, **flag it low-confidence** on the report.

## Golden rules
- **Never send the answer key to the browser.** Strip answer-bearing fields before emitting a question.
- **Idempotent imports.** Upsert competencies on `code`, questions on `source_ref`.
- **Resumable.** A page reload re-emits the pending question; never double-count an answer (unique `(session, question_number)`).
- **Log every LLM call + grade.** You'll need it to debug quality.
