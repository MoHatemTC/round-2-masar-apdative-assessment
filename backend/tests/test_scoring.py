"""Tests for app/services/scoring.py — scoring, band mapping, low-confidence flags."""
from __future__ import annotations

import pytest

from app.services.scoring import (
    CAP_CONVERGED_REASON,
    CONFIDENCE_TARGET,
    MAX_QUESTIONS,
    CompetencyResult,
    band_for_pct,
    build_final_report,
    competency_result_from_state,
    final_report_row,
    is_low_confidence,
    pct_for_level,
    score_competency,
    score_overall,
    session_competency_result_row,
)


# ── pct_for_level ────────────────────────────────────────────────────────────
class TestPctForLevel:
    @pytest.mark.parametrize(
        "level,expected_pct",
        [(1, 20), (2, 40), (3, 60), (4, 80), (5, 100)],
    )
    def test_integer_levels(self, level, expected_pct):
        assert pct_for_level(level) == expected_pct

    def test_clamps_below_range(self):
        assert pct_for_level(0) == 20

    def test_clamps_above_range(self):
        assert pct_for_level(9) == 100

    def test_returns_int_not_float(self):
        # Aligns with the DB's integer level model — no fractional pct values.
        assert isinstance(pct_for_level(3), int)


# ── band_for_pct ─────────────────────────────────────────────────────────────
class TestBandForPct:
    @pytest.mark.parametrize(
        "pct,expected_level,expected_label",
        [
            (0, 1, "Novice"),
            (1, 1, "Novice"),
            (20, 1, "Novice"),          # inclusive upper boundary
            (21, 2, "Developing"),      # just above boundary
            (40, 2, "Developing"),
            (41, 3, "Proficient"),
            (60, 3, "Proficient"),
            (61, 4, "Advanced"),
            (80, 4, "Advanced"),
            (81, 5, "Expert"),
            (100, 5, "Expert"),
        ],
    )
    def test_band_boundaries(self, pct, expected_level, expected_label):
        level, label = band_for_pct(pct)
        assert level == expected_level
        assert label == expected_label

    def test_pct_over_100_resolves_to_expert(self):
        # Defensive: shouldn't happen upstream, but must not crash or fall through.
        level, label = band_for_pct(150)
        assert (level, label) == (5, "Expert")


# ── CompetencyResult validation ──────────────────────────────────────────────
class TestCompetencyResultValidation:
    def test_valid_result_constructs(self):
        r = CompetencyResult(competency_id="c1", level=3, confidence=0.8)
        assert r.level == 3

    @pytest.mark.parametrize("bad_level", [0, 6, -1])
    def test_rejects_level_out_of_range(self, bad_level):
        with pytest.raises(ValueError):
            CompetencyResult(competency_id="c1", level=bad_level, confidence=0.5)

    @pytest.mark.parametrize("non_int_level", [3.5, "3", None])
    def test_rejects_non_integer_level(self, non_int_level):
        # DB model is integer 1..5 — no fractional or string levels allowed.
        with pytest.raises(ValueError):
            CompetencyResult(competency_id="c1", level=non_int_level, confidence=0.5)

    def test_rejects_bool_level(self):
        # bool is technically an int subclass in Python; must not sneak through.
        with pytest.raises(ValueError):
            CompetencyResult(competency_id="c1", level=True, confidence=0.5)

    @pytest.mark.parametrize("bad_confidence", [-0.1, 1.1, 2])
    def test_rejects_confidence_out_of_range(self, bad_confidence):
        with pytest.raises(ValueError):
            CompetencyResult(competency_id="c1", level=3, confidence=bad_confidence)

    def test_rejects_invalid_converged_reason(self):
        with pytest.raises(ValueError):
            CompetencyResult(
                competency_id="c1", level=3, confidence=0.5, converged_reason="timeout"
            )

    def test_rejects_negative_questions_asked(self):
        with pytest.raises(ValueError):
            CompetencyResult(
                competency_id="c1", level=3, confidence=0.5, questions_asked=-1
            )


# ── is_low_confidence ─────────────────────────────────────────────────────────
class TestLowConfidenceFlag:
    def test_cap_converged_below_target_is_low_confidence(self):
        r = CompetencyResult(
            competency_id="c1",
            level=3,
            confidence=0.6,
            converged_reason=CAP_CONVERGED_REASON,
            questions_asked=MAX_QUESTIONS,
        )
        assert is_low_confidence(r) is True

    def test_cap_converged_but_confidence_reached_target_anyway(self):
        # Edge case: hit the cap on the same turn confidence crossed the target.
        # Should NOT be flagged since it did in fact reach CONFIDENCE_TARGET.
        r = CompetencyResult(
            competency_id="c1",
            level=4,
            confidence=CONFIDENCE_TARGET,
            converged_reason=CAP_CONVERGED_REASON,
            questions_asked=MAX_QUESTIONS,
        )
        assert is_low_confidence(r) is False

    def test_converged_via_confidence_is_never_low_confidence(self):
        r = CompetencyResult(
            competency_id="c1",
            level=5,
            confidence=0.95,
            converged_reason="confidence",
            questions_asked=4,
        )
        assert is_low_confidence(r) is False

    def test_converged_via_stable_is_never_low_confidence(self):
        r = CompetencyResult(
            competency_id="c1",
            level=3,
            confidence=0.5,  # low confidence, but stability is what stopped it, not the cap
            converged_reason="stable",
            questions_asked=5,
        )
        assert is_low_confidence(r) is False

    def test_stable_at_exactly_max_questions_is_not_low_confidence(self):
        # Regression test: a competency that happened to take exactly MAX_QUESTIONS
        # turns to stabilize is 'stable', not 'cap-converged'. questions_asked alone
        # must NEVER override an explicit converged_reason of 'stable' or 'confidence'.
        r = CompetencyResult(
            competency_id="c1",
            level=3,
            confidence=0.4,  # deliberately low, to prove the reason (not the count) governs
            converged_reason="stable",
            questions_asked=MAX_QUESTIONS,
        )
        assert is_low_confidence(r) is False

    def test_confidence_at_exactly_max_questions_is_not_low_confidence(self):
        r = CompetencyResult(
            competency_id="c1",
            level=5,
            confidence=0.3,
            converged_reason="confidence",
            questions_asked=MAX_QUESTIONS,
        )
        assert is_low_confidence(r) is False

    def test_hit_cap_without_explicit_reason_still_flagged(self):
        # Defensive fallback only: no converged_reason recorded at all, but
        # questions_asked reached the cap — still treated as cap-converged.
        r = CompetencyResult(
            competency_id="c1",
            level=2,
            confidence=0.3,
            converged_reason=None,
            questions_asked=MAX_QUESTIONS,
        )
        assert is_low_confidence(r) is True

    def test_no_reason_and_under_cap_is_not_flagged(self):
        r = CompetencyResult(
            competency_id="c1",
            level=2,
            confidence=0.3,
            converged_reason=None,
            questions_asked=3,
        )
        assert is_low_confidence(r) is False


# ── score_competency ──────────────────────────────────────────────────────────
class TestScoreCompetency:
    def test_shape_and_values(self):
        r = CompetencyResult(
            competency_id="python",
            level=4,
            confidence=0.95,
            converged_reason="confidence",
            questions_asked=5,
        )
        result = score_competency(r)
        assert result == {
            "competency_id": "python",
            "level": 4,
            "pct": 80,
            "band_level": 4,
            "band_label": "Advanced",
            "confidence": 0.95,
            "converged_reason": "confidence",
            "questions_asked": 5,
            "low_confidence": False,
        }

    def test_low_confidence_surfaces_in_dict(self):
        r = CompetencyResult(
            competency_id="sql",
            level=2,
            confidence=0.4,
            converged_reason=CAP_CONVERGED_REASON,
            questions_asked=MAX_QUESTIONS,
        )
        result = score_competency(r)
        assert result["low_confidence"] is True
        assert result["band_label"] == "Developing"


# ── score_overall ─────────────────────────────────────────────────────────────
class TestScoreOverall:
    def test_mean_of_percentages(self):
        results = [
            CompetencyResult(competency_id="a", level=5, confidence=0.9),
            CompetencyResult(competency_id="b", level=3, confidence=0.9),
        ]
        # mean(level*20) = mean(100, 60) = 80
        overall = score_overall(results)
        assert overall["overall_pct"] == 80
        assert overall["overall_level"] == 4
        assert overall["level_label"] == "Advanced"

    def test_single_competency(self):
        results = [CompetencyResult(competency_id="a", level=1, confidence=0.5)]
        overall = score_overall(results)
        assert overall["overall_pct"] == 20
        assert overall["level_label"] == "Novice"

    def test_uneven_average_rounds_correctly(self):
        results = [
            CompetencyResult(competency_id="a", level=5, confidence=0.9),
            CompetencyResult(competency_id="b", level=5, confidence=0.9),
            CompetencyResult(competency_id="c", level=3, confidence=0.9),
        ]
        # mean(100, 100, 60) = 86.666...
        overall = score_overall(results)
        assert overall["overall_pct"] == pytest.approx(86.67, abs=0.01)
        assert overall["level_label"] == "Expert"

    def test_empty_results_raises(self):
        with pytest.raises(ValueError):
            score_overall([])


# ── build_final_report ────────────────────────────────────────────────────────
class TestBuildFinalReport:
    def test_full_report_shape(self):
        results = [
            CompetencyResult(
                competency_id="python", level=5, confidence=0.95, converged_reason="confidence"
            ),
            CompetencyResult(
                competency_id="sql",
                level=2,
                confidence=0.4,
                converged_reason=CAP_CONVERGED_REASON,
                questions_asked=MAX_QUESTIONS,
            ),
        ]
        report = build_final_report("session-123", results)

        assert report["session_id"] == "session-123"
        assert report["overall_pct"] == 70  # mean(100, 40)
        assert set(report["skill_scores"].keys()) == {"python", "sql"}
        assert report["skill_scores"]["python"]["low_confidence"] is False
        assert report["skill_scores"]["sql"]["low_confidence"] is True
        # Rolls up to true if ANY competency is low-confidence.
        assert report["has_low_confidence"] is True

    def test_no_low_confidence_competencies_rolls_up_false(self):
        results = [
            CompetencyResult(competency_id="a", level=4, confidence=0.92, converged_reason="confidence"),
            CompetencyResult(competency_id="b", level=3, confidence=0.91, converged_reason="stable"),
        ]
        report = build_final_report("session-456", results)
        assert report["has_low_confidence"] is False

    def test_low_confidence_not_falsely_triggered_by_stable_at_cap(self):
        # A session where every competency stabilized (even one that took the full
        # MAX_QUESTIONS turns) must not be flagged low-confidence overall.
        results = [
            CompetencyResult(
                competency_id="a", level=3, confidence=0.5,
                converged_reason="stable", questions_asked=MAX_QUESTIONS,
            ),
            CompetencyResult(competency_id="b", level=4, confidence=0.93, converged_reason="confidence"),
        ]
        report = build_final_report("session-789", results)
        assert report["has_low_confidence"] is False

    def test_empty_results_raises(self):
        with pytest.raises(ValueError):
            build_final_report("session-000", [])


# ── finalize() integration helpers ─────────────────────────────────────────────
class TestFinalizeIntegrationHelpers:
    """Covers the dict-shaping helpers finalize() uses to persist rows, without
    touching a real DB — these are pure functions over agent_state's per_competency dict."""

    def test_competency_result_from_state_rounds_level(self):
        pc = {"level": 3.7, "confidence": 0.85, "converged_reason": "confidence", "questions_asked": 4}
        result = competency_result_from_state("comp-1", pc)
        assert result.level == 4  # rounded to nearest int
        assert result.competency_id == "comp-1"

    def test_competency_result_from_state_missing_optional_fields(self):
        pc = {"level": 2, "confidence": 0.3}
        result = competency_result_from_state("comp-2", pc)
        assert result.converged_reason is None
        assert result.questions_asked is None

    def test_session_competency_result_row_shape(self):
        pc = {"level": 4, "confidence": 0.95, "self_rating": 3, "initial_estimate": 4,
              "converged_reason": "confidence", "questions_asked": 5}
        result = competency_result_from_state("comp-1", pc)
        row = session_competency_result_row("session-abc", pc, result)
        assert row == {
            "session_id": "session-abc",
            "competency_id": "comp-1",
            "self_rating": 3,
            "initial_estimate": 4,
            "final_level": 4,
            "final_confidence": 0.95,
            "questions_asked": 5,
            "converged_reason": "confidence",
            "low_confidence": False,
        }

    def test_final_report_row_shape(self):
        results = [
            CompetencyResult(competency_id="a", level=5, confidence=0.9, converged_reason="confidence"),
            CompetencyResult(competency_id="b", level=3, confidence=0.9, converged_reason="stable"),
        ]
        row = final_report_row("session-xyz", results)
        assert row["session_id"] == "session-xyz"
        assert row["overall_pct"] == 80
        assert row["overall_level"] == 4
        assert row["level_label"] == "Advanced"
        assert row["has_low_confidence"] is False
        assert set(row["skill_scores"].keys()) == {"a", "b"}