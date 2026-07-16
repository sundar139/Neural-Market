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
