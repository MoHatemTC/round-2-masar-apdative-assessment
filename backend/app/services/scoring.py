"""Scoring, band mapping, and low-confidence detection for `final_reports`.
   [Scoring, Reporting, Email & Observability lane — self-contained vertical slice]

Given contract (docs/ARCHITECTURE.md § Scoring, § Bank exhaustion):
    pct = level * 20
    bands: 0-20 Novice · 21-40 Developing · 41-60 Proficient · 61-80 Advanced · 81-100 Expert
    overall % = mean(level * 20) across competencies, mapped to the same bands.
    low_confidence: a competency converged ONLY by hitting the question cap
        (converged_reason == 'max_questions') while still below CONFIDENCE_TARGET.
        A 'stable' or 'confidence' convergence is NEVER low-confidence, even if it
        happened to take MAX_QUESTIONS turns to get there — the reason it stopped is
        what matters, not the raw question count.

This module is pure/deterministic (no DB, no LLM calls) so it can be used both by the
adaptive loop's `finalize()` step and independently by report/email rendering code.
The CONFIDENCE_TARGET / MAX_QUESTIONS knobs are duplicated (not imported) from
app/agent/adaptive_loop.py on purpose, per the "self-contained vertical slice, don't
depend on/modify other lanes' modules" scope — keep the two in sync with
docs/ARCHITECTURE.md if the knobs ever change.

`level` is typed and validated as an `int` in 1..5 throughout this module, matching the
Postgres integer columns (`final_level`, `overall_level`, etc.) defined in
backend/migrations/005_reports.sql — there is no fractional-level concept anywhere in
the DB model, so none is allowed here either.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Optional

# ── Convergence knobs (mirrors docs/ARCHITECTURE.md; kept consistent across lanes) ──
CONFIDENCE_TARGET = 0.90
MAX_QUESTIONS = 10
CAP_CONVERGED_REASON = "max_questions"
VALID_CONVERGED_REASONS = {"confidence", "stable", CAP_CONVERGED_REASON}

# (ceiling_pct, level, label) — ceilings are inclusive upper bounds, checked in order.
LEVEL_BANDS: list[tuple[int, int, str]] = [
    (20, 1, "Novice"),
    (40, 2, "Developing"),
    (60, 3, "Proficient"),
    (80, 4, "Advanced"),
    (100, 5, "Expert"),
]


def pct_for_level(level: int) -> int:
    """`level * 20`. `level` is clamped to the valid 1..5 range before scoring so a bad
    upstream value can't produce an out-of-range percentage. Returns an int, matching the
    DB's integer level model (1..5 always maps to an exact multiple of 20)."""
    clamped = max(1, min(5, level))
    return clamped * 20


def band_for_pct(pct: float) -> tuple[int, str]:
    """Map a 0-100 percentage onto one of the five named bands."""
    for ceiling, lvl, label in LEVEL_BANDS:
        if pct <= ceiling:
            return lvl, label
    return 5, "Expert"  # pct > 100 (shouldn't happen) still resolves to the top band


@dataclass
class CompetencyResult:
    """One row's worth of verified data for a single competency, as produced by
    `check_convergence` / `estimate` in the adaptive loop. Matches
    `session_competency_results` (see backend/migrations/005_reports.sql).

    `level` is an int in 1..5 — the DB model has no fractional level, so callers must
    round/argmax to an int (e.g. `int(round(pc['level']))`) before constructing this.
    """

    competency_id: str
    level: int                              # verified 1..5 level (DB: integer)
    confidence: float                       # 0..1
    converged_reason: Optional[str] = None  # 'confidence' | 'stable' | 'max_questions'
    questions_asked: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.level, int) or isinstance(self.level, bool):
            raise ValueError(
                f"level must be an int in 1..5 (matches the DB's integer model), "
                f"got {self.level!r} ({type(self.level).__name__})"
            )
        if not (1 <= self.level <= 5):
            raise ValueError(f"level must be within 1..5, got {self.level!r}")
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be within 0..1, got {self.confidence!r}")
        if self.converged_reason is not None and self.converged_reason not in VALID_CONVERGED_REASONS:
            raise ValueError(
                f"converged_reason must be one of {sorted(VALID_CONVERGED_REASONS)} or None, "
                f"got {self.converged_reason!r}"
            )
        if self.questions_asked is not None and self.questions_asked < 0:
            raise ValueError(f"questions_asked must be >= 0, got {self.questions_asked!r}")


def is_low_confidence(result: CompetencyResult) -> bool:
    """True only for the "cap-converged" case: the session stopped probing this
    competency specifically because it hit MAX_QUESTIONS, never actually reaching
    CONFIDENCE_TARGET (and never stabilizing).

    IMPORTANT: an explicit converged_reason of 'confidence' or 'stable' is authoritative
    and is NEVER overridden by questions_asked — a competency that happened to take
    exactly MAX_QUESTIONS turns to stabilize is not "cap-converged," it's stable. The
    questions_asked fallback below only fires when converged_reason wasn't recorded at
    all (defensive default for older/partial state), not to second-guess a reason that
    was explicitly set.
    """
    if result.converged_reason is not None:
        cap_converged = result.converged_reason == CAP_CONVERGED_REASON
    else:
        cap_converged = (
            result.questions_asked is not None and result.questions_asked >= MAX_QUESTIONS
        )
    return cap_converged and result.confidence < CONFIDENCE_TARGET


def score_competency(result: CompetencyResult) -> dict:
    """Full per-competency scoring row for `final_reports.skill_scores`."""
    pct = pct_for_level(result.level)
    band_level, band_label = band_for_pct(pct)
    return {
        "competency_id": result.competency_id,
        "level": result.level,
        "pct": pct,
        "band_level": band_level,
        "band_label": band_label,
        "confidence": result.confidence,
        "converged_reason": result.converged_reason,
        "questions_asked": result.questions_asked,
        "low_confidence": is_low_confidence(result),
    }


def score_overall(results: Iterable[CompetencyResult]) -> dict:
    """Overall %/band: `mean(level * 20)` across all competencies, per the given contract
    (mean of the *percentages*, equivalent to mean(level) * 20)."""
    results = list(results)
    if not results:
        raise ValueError("score_overall requires at least one competency result")
    overall_pct = round(mean(pct_for_level(r.level) for r in results), 2)
    overall_level, level_label = band_for_pct(overall_pct)
    return {
        "overall_pct": overall_pct,
        "overall_level": overall_level,
        "level_label": level_label,
    }


def build_final_report(session_id: str, results: Iterable[CompetencyResult]) -> dict:
    """Assemble a full `final_reports` row (overall %/band + skill_scores + the
    has_low_confidence rollup) ready for insertion. Pure data shaping — callers own the
    actual DB write."""
    results = list(results)
    overall = score_overall(results)
    skill_scores = {r.competency_id: score_competency(r) for r in results}
    has_low_confidence = any(s["low_confidence"] for s in skill_scores.values())
    return {
        "session_id": session_id,
        **overall,
        "skill_scores": skill_scores,
        "has_low_confidence": has_low_confidence,
    }


# ── Integration helpers for finalize() ───────────────────────────────────────────
# These build plain dict rows ready for `db.table(...).upsert(...)`, so the actual DB
# I/O stays in the adaptive loop (which owns the `db` client) while all the scoring
# math and validation stays here, in one tested place.

def competency_result_from_state(competency_id: str, pc: dict) -> CompetencyResult:
    """Build a validated CompetencyResult from an agent_state `per_competency[cid]` entry."""
    return CompetencyResult(
        competency_id=competency_id,
        level=int(round(pc["level"])),
        confidence=pc["confidence"],
        converged_reason=pc.get("converged_reason"),
        questions_asked=pc.get("questions_asked"),
    )


def session_competency_result_row(session_id: str, pc: dict, result: CompetencyResult) -> dict:
    """A `session_competency_results` row, matching the schema in 005_reports.sql exactly."""
    scored = score_competency(result)
    return {
        "session_id": session_id,
        "competency_id": result.competency_id,
        "self_rating": pc.get("self_rating"),
        "initial_estimate": pc.get("initial_estimate"),
        "final_level": result.level,
        "final_confidence": result.confidence,
        "questions_asked": result.questions_asked,
        "converged_reason": result.converged_reason,
        "low_confidence": scored["low_confidence"],
    }


def final_report_row(session_id: str, results: Iterable[CompetencyResult]) -> dict:
    """A `final_reports` row, matching the schema in 005_reports.sql exactly."""
    report = build_final_report(session_id, results)
    return {
        "session_id": report["session_id"],
        "overall_pct": report["overall_pct"],
        "overall_level": report["overall_level"],
        "level_label": report["level_label"],
        "skill_scores": report["skill_scores"],
        "has_low_confidence": report["has_low_confidence"],
    }