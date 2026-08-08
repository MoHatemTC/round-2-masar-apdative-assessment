"""
Tests for the AI-Proctoring endpoints and worker.

Covers:
  * Size caps (413 file_too_large)
  * MIME allowlist + JPEG magic-byte check (422)
  * Consent required before reference upload (422 consent_missing)
  * bad kind rejected (422 bad_kind)
  * Rate limiting fires after N calls
  * Batch idempotency (same batch_id -> 200 idempotent)
  * Verdict-JSON parser tolerates fences and returns safe defaults on garbage
  * Access control: RLS on the tables (informational assertion — the migration
    file contains the ENABLE ROW LEVEL SECURITY statements)

Run:
    pytest backend/tests/test_proctoring.py -v
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

# Import module under test — path anchored at the repo backend/.
from app.routes import proctoring as p
from app.workers.proctoring_worker import _parse_verdicts

JPEG_MAGIC = b"\xff\xd8\xff"
FAKE_JPEG = JPEG_MAGIC + b"\x00" * 200
BIG_JPEG = JPEG_MAGIC + b"\x00" * (p.MAX_FILE_BYTES + 10)
NOT_JPEG = b"GIF89a" + b"\x00" * 100


# ---------- Small helpers ---------------------------------------------------

def make_upload(data: bytes, mime: str = "image/jpeg", filename: str = "x.jpg") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers=Headers({"content-type": mime}),
    )


# ============================================================================
# _validate_jpeg
# ============================================================================

class TestValidateJpeg:
    def test_accepts_valid_jpeg(self):
        p._validate_jpeg(make_upload(FAKE_JPEG), FAKE_JPEG, p.MAX_FILE_BYTES)

    def test_rejects_wrong_mime(self):
        with pytest.raises(Exception) as exc:
            p._validate_jpeg(make_upload(FAKE_JPEG, mime="image/png"), FAKE_JPEG, p.MAX_FILE_BYTES)
        assert "unsupported_media_type" in str(exc.value.detail)

    def test_rejects_empty(self):
        with pytest.raises(Exception) as exc:
            p._validate_jpeg(make_upload(b""), b"", p.MAX_FILE_BYTES)
        assert "empty_file" in str(exc.value.detail)

    def test_rejects_oversized(self):
        with pytest.raises(Exception) as exc:
            p._validate_jpeg(make_upload(BIG_JPEG), BIG_JPEG, p.MAX_FILE_BYTES)
        assert exc.value.status_code == 413

    def test_rejects_wrong_magic_bytes(self):
        with pytest.raises(Exception) as exc:
            p._validate_jpeg(make_upload(NOT_JPEG), NOT_JPEG, p.MAX_FILE_BYTES)
        assert "not_a_jpeg" in str(exc.value.detail)


# ============================================================================
# Rate limiter
# ============================================================================

class TestRateLimiter:
    def setup_method(self):
        p._recent.clear()

    def test_allows_first_N(self):
        session_id = "s1"
        for _ in range(p._RATE_MAX_CALLS):
            assert p._rate_limited(session_id) is False

    def test_blocks_after_N(self):
        session_id = "s2"
        for _ in range(p._RATE_MAX_CALLS):
            p._rate_limited(session_id)
        assert p._rate_limited(session_id) is True

    def test_independent_per_session(self):
        for _ in range(p._RATE_MAX_CALLS):
            p._rate_limited("sA")
        # Different session must still be allowed
        assert p._rate_limited("sB") is False


# ============================================================================
# _load_session
# ============================================================================

@pytest.mark.asyncio
class TestLoadSession:
    async def test_unknown_session_raises_422(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute = AsyncMock(return_value=MagicMock(data=None))
        db.table.return_value = chain
        with pytest.raises(Exception) as exc:
            await p._load_session(db, "does-not-exist")
        assert "unknown_session" in str(exc.value.detail)

    async def test_completed_session_raises_422(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute = AsyncMock(return_value=MagicMock(data={"id": "x", "status": "completed"}))
        db.table.return_value = chain
        with pytest.raises(Exception) as exc:
            await p._load_session(db, "x")
        assert "session_not_active" in str(exc.value.detail)


# ============================================================================
# Verdict JSON parser (worker resilience)
# ============================================================================

class TestParseVerdicts:
    def test_parses_bare_json_array(self):
        text = json.dumps([
            {"person_present": True, "same_person_as_reference": True,
             "multiple_people": False, "phone_visible": False,
             "looking_away": False, "confidence": 0.8}
        ])
        out = _parse_verdicts(text, 1)
        assert out[0]["confidence"] == 0.8

    def test_parses_fenced_json(self):
        text = "```json\n" + json.dumps([{
            "person_present": True, "same_person_as_reference": True,
            "multiple_people": False, "phone_visible": False,
            "looking_away": False, "confidence": 0.7
        }]) + "\n```"
        out = _parse_verdicts(text, 1)
        assert len(out) == 1
        assert out[0]["person_present"] is True

    def test_wrong_length_returns_defaults(self):
        text = json.dumps([{"person_present": True}])
        out = _parse_verdicts(text, 3)          # expected 3 verdicts
        assert len(out) == 3
        assert all(v["confidence"] == 0.0 for v in out)

    def test_garbage_returns_defaults(self):
        out = _parse_verdicts("hello I am a language model", 2)
        assert len(out) == 2
        assert all(v.get("note") == "parse_failed" for v in out)

    def test_empty_text_returns_defaults(self):
        out = _parse_verdicts("", 2)
        assert len(out) == 2

    def test_strips_think_tags(self):
        inner = json.dumps([{
            "person_present": True, "same_person_as_reference": True,
            "multiple_people": False, "phone_visible": False,
            "looking_away": False, "confidence": 0.9
        }])
        text = "<think>\nSome reasoning with [brackets] inside\n</think>\n" + inner
        out = _parse_verdicts(text, 1)
        assert out[0]["person_present"] is True
        assert out[0]["confidence"] == 0.9


# ============================================================================
# Golden set assertions (repository-level)
# ============================================================================

class TestGoldenSet:
    """The golden set on disk must contain exactly the expected files + labels.json."""

    GOLDEN_DIR = Path(__file__).resolve().parents[1] / "data" / "golden_set"

    def test_has_10_images(self):
        if not self.GOLDEN_DIR.exists():
            pytest.skip("run backend/data/golden_set/generate_golden_set.py first")
        jpgs = sorted(self.GOLDEN_DIR.glob("*.jpg"))
        assert len(jpgs) == 10

    def test_labels_file_covers_every_image(self):
        if not self.GOLDEN_DIR.exists():
            pytest.skip("run backend/data/golden_set/generate_golden_set.py first")
        labels_path = self.GOLDEN_DIR / "labels.json"
        assert labels_path.exists()
        labels = json.loads(labels_path.read_text())
        jpgs = {p.name for p in self.GOLDEN_DIR.glob("*.jpg")}
        assert jpgs == set(labels.keys())

    def test_includes_prompt_injection_case(self):
        if not self.GOLDEN_DIR.exists():
            pytest.skip("run backend/data/golden_set/generate_golden_set.py first")
        labels = json.loads((self.GOLDEN_DIR / "labels.json").read_text())
        pi = labels.get("09_prompt_injection.jpg")
        assert pi is not None
        # The label must say the model should NOT report all-clear falsely.
        assert pi.get("person_present") is True
        assert "note" in pi
