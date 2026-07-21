"""Tests for Week 1 - Intake Foundation: session start/intake endpoints + starting-prior logic.

Covers:
  - POST /session/start: happy path, missing/invalid assessment.
  - POST /session/{id}/intake: happy path (persists self-ratings keyed by competency,
    mirrors into session_self_ratings, flips status, returns priors), validation errors,
    unknown session.
  - app.services.prior.compute_prior / compute_priors: the self-rating and default-3 fallbacks
    required by this task, plus the blended-with-CV branch for forward compatibility.
"""
from __future__ import annotations

import io

from app.services.prior import DEFAULT_PRIOR, compute_prior, compute_priors

COMPETENCY_A = "11111111-1111-1111-1111-111111111111"
COMPETENCY_B = "22222222-2222-2222-2222-222222222222"


# ── POST /session/start ───────────────────────────────────────────────────────

# ── POST /session/{id}/cv ──────────────────────────────────────────────────────

def test_upload_cv_txt_stores_extracted_text(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})

    resp = client.post(
        f"/session/{session['id']}/cv",
        files={"file": ("resume.txt", b"5 years of Python and SQL experience.", "text/plain")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "resume.txt"
    assert body["characters_extracted"] == len("5 years of Python and SQL experience.")

    stored = fake_db.tables["sessions"][0]["cv_json"]
    assert stored["filename"] == "resume.txt"
    assert stored["raw_text"] == "5 years of Python and SQL experience."
    assert stored["uploaded_at"]  # timestamp was set


def test_upload_cv_404_when_session_missing(client):
    resp = client.post(
        "/session/unknown-id/cv",
        files={"file": ("resume.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 404


def test_upload_cv_422_when_file_empty(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(
        f"/session/{session['id']}/cv",
        files={"file": ("resume.txt", b"", "text/plain")},
    )
    assert resp.status_code == 422
    assert "empty" in resp.json()["detail"].lower()


def test_upload_cv_422_when_too_large(client, fake_db):
    from app.routes.candidate_intake import MAX_CV_BYTES
    session = fake_db.seed("sessions", {"status": "identity"})
    oversized = b"x" * (MAX_CV_BYTES + 1)
    resp = client.post(
        f"/session/{session['id']}/cv",
        files={"file": ("resume.txt", oversized, "text/plain")},
    )
    assert resp.status_code == 422
    assert "too large" in resp.json()["detail"].lower()


def test_upload_cv_422_when_unsupported_extension(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(
        f"/session/{session['id']}/cv",
        files={"file": ("resume.docx", b"whatever bytes", "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert "unsupported" in resp.json()["detail"].lower()


def test_upload_cv_handles_a_real_pdf_via_pypdf(client, fake_db):
    """Exercises the real pypdf extraction path (not mocked) against an actual, validly-formed
    PDF. A blank page has no text to extract, so this must 422 with a clear message rather than
    silently storing an empty CV — proving the pypdf integration itself works end to end."""
    from pypdf import PdfWriter
    session = fake_db.seed("sessions", {"status": "identity"})

    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    resp = client.post(
        f"/session/{session['id']}/cv",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert resp.status_code == 422
    assert "extract" in resp.json()["detail"].lower()


def test_start_session_creates_row_and_returns_id(client, fake_db):
    assessment = fake_db.seed("assessments", {"id": "a-1", "title": "AI Engineer"})

    resp = client.post("/session/start", json={
        "assessment_id": assessment["id"],
        "candidate_name": "Ada",
        "candidate_email": "ada@example.com",
    })

    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id

    stored = fake_db.tables["sessions"][0]
    assert stored["assessment_id"] == assessment["id"]
    assert stored["candidate_name"] == "Ada"
    assert stored["status"] == "identity"
    assert stored["intake_answers"] == {}


def test_start_session_404_when_assessment_missing(client, fake_db):
    resp = client.post("/session/start", json={"assessment_id": "does-not-exist"})
    assert resp.status_code == 404
    assert fake_db.tables.get("sessions", []) == []  # no orphaned session created


def test_start_session_422_when_assessment_id_missing(client):
    resp = client.post("/session/start", json={"candidate_name": "Ada"})
    assert resp.status_code == 422


def test_start_session_422_when_assessment_id_blank(client):
    resp = client.post("/session/start", json={"assessment_id": "   "})
    assert resp.status_code == 422


# ── POST /session/{id}/intake ─────────────────────────────────────────────────

def test_submit_intake_persists_ratings_and_returns_priors(client, fake_db):
    fake_db.seed("assessments", {"id": "a-1"})
    fake_db.seed("competencies", {"id": COMPETENCY_A, "code": "python"})
    fake_db.seed("competencies", {"id": COMPETENCY_B, "code": "sql"})
    session = fake_db.seed("sessions", {
        "assessment_id": "a-1", "status": "identity", "intake_answers": {}, "cv_json": None,
    })

    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {COMPETENCY_A: 4, COMPETENCY_B: 2},
    })

    assert resp.status_code == 200
    body = resp.json()
    assert body["self_ratings"] == {COMPETENCY_A: 4, COMPETENCY_B: 2}
    # No CV available at intake time -> prior falls back to the self-rating itself.
    assert body["priors"] == {COMPETENCY_A: 4, COMPETENCY_B: 2}

    updated = fake_db.tables["sessions"][0]
    assert updated["status"] == "in_progress"
    assert updated["intake_answers"] == {COMPETENCY_A: 4, COMPETENCY_B: 2}
    assert updated["intake_submitted_at"]  # timestamp was set

    mirrored = {r["competency_id"]: r["self_rating"] for r in fake_db.tables["session_self_ratings"]}
    assert mirrored == {COMPETENCY_A: 4, COMPETENCY_B: 2}


def test_submit_intake_404_when_session_missing(client):
    resp = client.post("/session/unknown-id/intake", json={"self_ratings": {COMPETENCY_A: 3}})
    assert resp.status_code == 404


def test_submit_intake_422_when_self_ratings_missing(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(f"/session/{session['id']}/intake", json={})
    assert resp.status_code == 422


def test_submit_intake_422_when_rating_out_of_range(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {COMPETENCY_A: 7},
    })
    assert resp.status_code == 422
    assert "between 1 and 5" in str(resp.json()["detail"])


def test_submit_intake_422_when_rating_not_numeric(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {COMPETENCY_A: "high"},
    })
    assert resp.status_code == 422


def test_submit_intake_422_when_competency_id_not_a_uuid(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {"not-a-real-uuid": 3},
    })
    assert resp.status_code == 422
    assert "not a valid competency id" in str(resp.json()["detail"])
    # Nothing should have been written — validation happens before any write.
    assert fake_db.tables.get("session_self_ratings", []) == []


def test_submit_intake_404_when_competency_id_unknown(client, fake_db):
    session = fake_db.seed("sessions", {"status": "identity"})
    # Syntactically a valid UUID, but no matching row in `competencies`.
    unknown_id = "99999999-9999-9999-9999-999999999999"
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {unknown_id: 3},
    })
    assert resp.status_code == 404
    assert unknown_id in str(resp.json()["detail"])
    # sessions.status must NOT have flipped to in_progress on a failed intake.
    assert fake_db.tables["sessions"][0]["status"] == "identity"


def test_submit_intake_succeeds_when_competency_exists(client, fake_db):
    fake_db.seed("competencies", {"id": COMPETENCY_A, "code": "python"})
    session = fake_db.seed("sessions", {"status": "identity"})
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {COMPETENCY_A: 4},
    })
    assert resp.status_code == 200


def test_submit_intake_keeps_cv_json_sent_at_start(client, fake_db):
    fake_db.seed("competencies", {"id": COMPETENCY_A, "code": "python"})
    session = fake_db.seed("sessions", {
        "status": "identity", "cv_json": {"raw_text": "resume..."},
    })
    resp = client.post(f"/session/{session['id']}/intake", json={
        "self_ratings": {COMPETENCY_A: 3},
    })
    assert resp.status_code == 200
    assert fake_db.tables["sessions"][0]["cv_json"] == {"raw_text": "resume..."}


# ── app.services.prior ────────────────────────────────────────────────────────

def test_compute_prior_defaults_to_three_when_neither_given():
    assert compute_prior(None, None) == DEFAULT_PRIOR == 3


def test_compute_prior_uses_self_rating_when_no_cv():
    for rating in (1, 2, 3, 4, 5):
        assert compute_prior(rating, None) == rating


def test_compute_prior_blends_when_both_given():
    # round(0.5*4 + 0.5*2) = round(3.0) = 3
    assert compute_prior(self_rating=2, cv_estimate=4) == 3


def test_compute_prior_rounds_half_up_not_to_even():
    # round(0.5*3 + 0.5*2) = round(2.5) -> 3 (half-up), not 2 (Python's banker's rounding)
    assert compute_prior(self_rating=2, cv_estimate=3) == 3
    assert compute_prior(self_rating=4, cv_estimate=3) == 4  # round(3.5) -> 4


def test_compute_prior_clamps_to_valid_range():
    assert compute_prior(self_rating=9, cv_estimate=None) == 5
    assert compute_prior(self_rating=0, cv_estimate=None) == 1


def test_compute_prior_delegates_to_priors_bridge(monkeypatch):
    """compute_prior must not reimplement the blend formula — it should call
    priors_bridge.blend_intake_signals and just clamp/round the result."""
    import app.services.prior as prior_module

    calls = []

    def fake_blend(self_rating, cv_estimate):
        calls.append((self_rating, cv_estimate))
        return 4.6  # deliberately not what the real formula would give, to prove it's actually used

    monkeypatch.setattr(prior_module, "blend_intake_signals", fake_blend)

    result = compute_prior(self_rating=2, cv_estimate=5)

    assert calls == [(2, 5)]      # called with our raw inputs, no pre-blending done locally
    assert result == 5            # round_half_up(4.6) = 5, proving the fake return value was used


def test_compute_priors_maps_every_competency():
    result = compute_priors({COMPETENCY_A: 5, COMPETENCY_B: 1}, cv_estimates=None)
    assert result == {COMPETENCY_A: 5, COMPETENCY_B: 1}


def test_compute_priors_blends_only_competencies_with_a_cv_estimate():
    result = compute_priors(
        self_ratings={COMPETENCY_A: 2, COMPETENCY_B: 4},
        cv_estimates={COMPETENCY_A: 4},  # no CV estimate for COMPETENCY_B
    )
    assert result[COMPETENCY_A] == 3   # blended: round(0.5*4 + 0.5*2)
    assert result[COMPETENCY_B] == 4   # self-rating only, no CV estimate available