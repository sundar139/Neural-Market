"""Integration tests for `data pilot recheck-cost` — offline, fake provider only."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app
from neuralmarket.data.acquisition.metadata_runner import IsolatedMetadataResult

pytestmark = pytest.mark.integration

runner = CliRunner()

_SUPPORTED = {
    "ARCX.PILLAR": ["definition", "ohlcv-1d", "statistics", "trades"],
    "OPRA.PILLAR": ["definition", "cbbo-1m", "trades"],
}


class _FakeProvider:
    def __init__(self) -> None:
        self.schema_calls: list[str] = []
        self.closed = False

    def list_schemas(self, *, dataset: str) -> list[str]:
        self.schema_calls.append(dataset)
        return _SUPPORTED[dataset]

    def close(self) -> None:
        self.closed = True


def _ok(cost: str) -> IsolatedMetadataResult:
    return IsolatedMetadataResult(
        endpoint_values={"cost": float(cost)},
        events=[],
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _fail() -> IsolatedMetadataResult:
    return IsolatedMetadataResult(
        events=[],
        failure_type="BentoServerError",
        failed_endpoint="cost",
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _prepare(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, cost: str
) -> tuple[Path, Path, str]:
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps({"placeholder": True}), encoding="utf-8")
    ckpt_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    manifest = tmp_path / "request_manifest.json"
    manifest.write_text(json.dumps({"plan_hash": "a" * 64}), encoding="utf-8")

    provider = _FakeProvider()
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "load_checkpoint", lambda *a, **k: object())
    monkeypatch.setattr(data_module, "_pilot_metadata_provider_factory", lambda: provider)
    monkeypatch.setattr(data_module, "_run_isolated_metadata", lambda **kw: _ok(cost))
    monkeypatch.setenv("DATABENTO_API_KEY", "offline-dummy")
    return checkpoint, manifest, ckpt_sha


def _args(checkpoint: Path, manifest: Path, sha: str, out: Path, attempts: Path) -> list[str]:
    return [
        "data",
        "pilot",
        "recheck-cost",
        "--checkpoint",
        str(checkpoint),
        "--request-manifest",
        str(manifest),
        "--expected-checkpoint-sha256",
        sha,
        "--output",
        str(out),
        "--attempt-manifest",
        str(attempts),
    ]


def test_recheck_cost_complete_and_ready(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.01")
    out = tmp_path / "evidence.json"
    attempts = tmp_path / "attempts.json"
    res = runner.invoke(app, _args(checkpoint, manifest, sha, out, attempts))
    assert res.exit_code == 0, res.output
    evidence = json.loads(out.read_text(encoding="utf-8"))
    assert evidence["status"] == "complete"
    assert evidence["authorization_ready"] is True
    assert evidence["provider_quote_count"] == 25
    assert evidence["unavailable_quote_count"] == 0
    assert evidence["purchase_authorized"] is False
    assert evidence["provider_call_inventory"]["timeseries_get_range"] == 0
    assert evidence["provider_call_inventory"]["list_schemas"] == 2
    # Parent symbology reached the quote layer for SPY.OPT.
    opt = [q for q in evidence["quotes"] if q["symbols"] == ["SPY.OPT"]]
    assert opt and all(q["stype_in"] == "parent" for q in opt)
    assert attempts.exists()


def test_recheck_cost_over_ceiling_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.20")
    out = tmp_path / "evidence.json"
    attempts = tmp_path / "attempts.json"
    res = runner.invoke(app, _args(checkpoint, manifest, sha, out, attempts))
    assert res.exit_code == 1
    evidence = json.loads(out.read_text(encoding="utf-8"))
    assert evidence["within_drift_ceiling"] is False
    assert evidence["authorization_ready"] is False


def test_recheck_cost_checkpoint_sha_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint, manifest, _ = _prepare(monkeypatch, tmp_path, cost="0.01")
    out = tmp_path / "evidence.json"
    attempts = tmp_path / "attempts.json"
    res = runner.invoke(app, _args(checkpoint, manifest, "0" * 64, out, attempts))
    assert res.exit_code == 1
    assert not out.exists()


def test_recheck_cost_never_imports_provider_namespaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    before = "databento" in sys.modules
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.01")
    out = tmp_path / "evidence.json"
    attempts = tmp_path / "attempts.json"
    runner.invoke(app, _args(checkpoint, manifest, sha, out, attempts))
    assert not ("databento" in sys.modules and not before)


def test_recheck_cost_resume_quotes_only_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.01")
    first = tmp_path / "first.json"
    first_attempts = tmp_path / "first-attempts.json"
    calls: list[str] = []

    def initial_quote(**kwargs):
        request_id = kwargs["request"].request_id
        calls.append(request_id)
        return _fail() if len(set(calls)) == 25 else _ok("0.0100")

    monkeypatch.setattr(data_module, "_run_isolated_metadata", initial_quote)
    initial = runner.invoke(app, _args(checkpoint, manifest, sha, first, first_attempts))
    assert initial.exit_code == 1
    payload = json.loads(first.read_text(encoding="utf-8"))
    preserved = next(quote for quote in payload["quotes"] if quote["status"] == "quoted")
    target = next(
        quote["request_id"] for quote in payload["quotes"] if quote["status"] == "unavailable"
    )
    calls.clear()
    monkeypatch.setattr(
        data_module,
        "_run_isolated_metadata",
        lambda **kwargs: calls.append(kwargs["request"].request_id) or _ok("0.02"),
    )
    final = tmp_path / "final.json"
    final_attempts = tmp_path / "final-attempts.json"
    resumed = runner.invoke(
        app,
        [*_args(checkpoint, manifest, sha, final, final_attempts), "--resume-from", str(first)],
    )
    assert resumed.exit_code == 0, resumed.output
    evidence = json.loads(final.read_text(encoding="utf-8"))
    final_preserved = next(
        quote for quote in evidence["quotes"] if quote["request_id"] == preserved["request_id"]
    )
    assert calls == [target]
    assert final_preserved == preserved
    assert evidence["completed_request_refetch_count"] == 0
    assert evidence["preserved_completed_quote_count"] == 24
    assert evidence["final_provider_quote_count"] == 25
    assert evidence["source_evidence_sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()


def test_recheck_cost_complete_resume_needs_no_key_or_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.01")
    first = tmp_path / "complete.json"
    first_attempts = tmp_path / "complete-attempts.json"
    initial = runner.invoke(app, _args(checkpoint, manifest, sha, first, first_attempts))
    assert initial.exit_code == 0
    monkeypatch.delenv("DATABENTO_API_KEY")
    monkeypatch.setattr(
        data_module,
        "_pilot_metadata_provider_factory",
        lambda: pytest.fail("complete resume must not construct provider"),
    )
    final = tmp_path / "noop.json"
    result = runner.invoke(
        app,
        [
            *_args(checkpoint, manifest, sha, final, tmp_path / "noop-attempts.json"),
            "--resume-from",
            str(first),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "no resume work is required" in result.output.lower()
    assert json.loads(final.read_text(encoding="utf-8"))["provider_call_inventory"]["get_cost"] == 0


def test_recheck_cost_invalid_resume_rejected_before_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint, manifest, sha = _prepare(monkeypatch, tmp_path, cost="0.01")
    source = tmp_path / "source.json"
    attempts = tmp_path / "source-attempts.json"
    assert runner.invoke(app, _args(checkpoint, manifest, sha, source, attempts)).exit_code == 0
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["quotes"][0]["dataset"] = "OTHER.DATASET"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        data_module,
        "_pilot_metadata_provider_factory",
        lambda: pytest.fail("invalid resume must not construct provider"),
    )
    result = runner.invoke(
        app,
        [
            *_args(checkpoint, manifest, sha, tmp_path / "never.json", tmp_path / "never-a.json"),
            "--resume-from",
            str(source),
        ],
    )
    assert result.exit_code == 1
