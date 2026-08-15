"""CLI integration: native execution-quote initialize-only with zero provider calls."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuralmarket.cli.main import app
from neuralmarket.data.acquisition.development_cost_quote import (
    DevelopmentQuoteBindings,
    validate_complete_development_cost_evidence,
)
from neuralmarket.data.acquisition.development_execution import (
    build_fresh_execution_quote_scope,
    derive_execution_quote_classification,
    load_development_execution_manifest,
    write_fresh_execution_quote_scope,
)

pytestmark = pytest.mark.integration

runner = CliRunner()

_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _ROOT / "reports/data/execution"
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _EXECUTION_DIR / "f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_EVIDENCE = _EXECUTION_DIR / "live_c1_20260814T191524Z_run10.local.json"
_HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    check=True,
    capture_output=True,
    text=True,
    cwd=_ROOT,
).stdout.strip()
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_PLAN_HASH = "1902157e61360897eb8cdb5a07f16877b15c0f56301f8584bfa03d0e95be25b5"
_MANIFEST_SHA = "5b64c5c398f4543c45a44fea24499765e7b6797b3250023a2b8c51281fdaf67f"
_MANIFEST_HASH = "303fcc84a2d7af0c13cca5bfeb54eb796a5536ce0630e6741f2c748f2563e4e9"
_EVIDENCE_FILE_SHA = "60032ab4f7536849104d12855adc5b5271b9e9ca4c8ceac158f509d1a121f111"
_PILOT_PLAN_SHA = "8b74ddf96873ffd8f08ace7e287eb24df130eb2483ac85a6f9af75355c66aafd"
_JOURNAL_SHA = "7eecde7bbd18b5928c6d5e82557db226f62e0556b4fe43dfd91e239083707c92"


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    execution = _EXECUTION_DIR / f"test_execution_quote_cli_{tmp_path.name}"
    execution.mkdir(parents=True, exist_ok=True)
    yield execution
    shutil.rmtree(execution, ignore_errors=True)


@pytest.fixture(scope="module")
def fresh_scope(workdir_factory=None) -> tuple[Path, str, str]:
    del workdir_factory
    manifest = load_development_execution_manifest(_MANIFEST)
    scope_payload = json.loads(_SCOPE_SRC.read_text(encoding="utf-8"))
    evidence_payload = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
    from neuralmarket.data.acquisition.development import DevelopmentRequest

    requests = [DevelopmentRequest.model_validate(item) for item in scope_payload["requests"]]
    bindings = DevelopmentQuoteBindings.model_validate(evidence_payload["bindings"])
    parent_evidence = validate_complete_development_cost_evidence(
        evidence_payload, expected_bindings=bindings, requests=requests
    )
    reusable_parents = {item["development_request_id"] for item in scope_payload["reusable"]}
    unavailable_parents = {item["development_request_id"] for item in scope_payload["unavailable"]}
    by_parent: dict[str, list] = {}
    for item in manifest.execution_requests:
        by_parent.setdefault(item.parent_request_id, []).append(item)
    excluded_reused = {by_parent[pid][0].execution_request_id for pid in reusable_parents}
    excluded_unavailable = {by_parent[pid][0].execution_request_id for pid in unavailable_parents}
    classification = derive_execution_quote_classification(
        manifest=manifest,
        excluded_reused_ids=excluded_reused,
        excluded_unavailable_ids=excluded_unavailable,
        accepted_parent_evidence=parent_evidence,
        source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
        source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
    )
    scope = build_fresh_execution_quote_scope(manifest=manifest, classification=classification)
    path = _EXECUTION_DIR / "test_fresh_execution_scope_gpt56.local.json"
    write_fresh_execution_quote_scope(path, scope)
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, scope.scope_hash, file_sha


def _args(workdir: Path, fresh_scope: tuple[Path, str, str]) -> list[str]:
    checkpoint = workdir / "execution-checkpoint.json"
    output = workdir / "execution-progress.json"
    scope_path, scope_hash, scope_sha = fresh_scope
    return [
        "data",
        "development",
        "execution-quote-cost",
        "--initialize-only",
        "--fresh-scope",
        str(scope_path),
        "--checkpoint",
        str(checkpoint),
        "--output",
        str(output),
        "--hard-timeout-seconds",
        "30",
        "--maximum-attempts",
        "2",
        "--total-deadline-seconds",
        "60",
        "--expected-repository-head",
        _HEAD,
        "--expected-plan-sha256",
        _PLAN_SHA,
        "--expected-plan-hash",
        _PLAN_HASH,
        "--expected-manifest-sha256",
        _MANIFEST_SHA,
        "--expected-manifest-hash",
        _MANIFEST_HASH,
        "--expected-fresh-scope-sha256",
        scope_sha,
        "--expected-fresh-scope-hash",
        scope_hash,
        "--expected-pilot-plan-sha256",
        _PILOT_PLAN_SHA,
        "--expected-journal-sha256",
        _JOURNAL_SHA,
    ]


class TestExecutionQuoteCli:
    def test_initialize_only_zero_provider_calls(self, workdir: Path, fresh_scope) -> None:
        result = runner.invoke(app, _args(workdir, fresh_scope))
        assert result.exit_code == 0, result.output
        summary = json.loads(result.output.strip().splitlines()[-1])
        assert summary["request_count"] == 58
        assert summary["metadata_operations"] == 0
        assert summary["status"] == "incomplete"
        assert summary["schema_version"] == "development-cost-progress-v1"
        checkpoint = workdir / "execution-checkpoint.json"
        assert checkpoint.exists()
        checkpoint_payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        counters = checkpoint_payload["provider_operation_counters"]
        assert (
            counters["get_record_count"]
            + counters["get_billable_size"]
            + counters["get_cost"]
            + counters["list_schemas"]
            == 0
        )
        output = workdir / "execution-progress.json"
        assert output.exists()

    def test_gate_fails_on_wrong_fresh_scope_hash(self, workdir: Path, fresh_scope) -> None:
        args = _args(workdir, fresh_scope)
        hash_index = args.index("--expected-fresh-scope-hash")
        args[hash_index + 1] = "0" * 64
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        assert "gate failed" in result.output
