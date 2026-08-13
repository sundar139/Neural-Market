import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from neuralmarket.cli import data as data_module
from neuralmarket.data.acquisition.authorization import RemainingRequestScope
from neuralmarket.data.acquisition.executor import (
    PilotExecutionCoordinator,
    RawAcquisitionResult,
    ValidationOnlyResult,
)
from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.acquisition.requests import AcquisitionRequest, load_pilot_config
from neuralmarket.data.raw.integrity import sha256_of_file

pytestmark = pytest.mark.integration


def test_raw_validated_paid_dbn_resumes_offline_without_paid_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The protected raw-validated request normalizes from its local DBN only."""
    root = Path(__file__).resolve().parents[2]
    source_journal = root / "data/state/pilot_acquisition_journal.sqlite"
    raw_path = (
        root
        / "data/raw/databento/pilot_january_2019/ARCX.PILLAR/ohlcv-1d"
        / "start_date=2019-01-02/end_date=2019-02-01/6b46de651d2cf921.dbn"
    )
    if not source_journal.is_file() or not raw_path.is_file():
        pytest.skip("protected production journal and paid DBN are not present")
    target_id = "6b46de651d2cf921"
    completed_id = "2750995e515e4f1a"
    journal_path = tmp_path / "journal.sqlite"
    shutil.copy2(source_journal, journal_path)
    # Seed the exact fixture state on the temporary copy. The test must not
    # depend on the mutable production journal still holding the historical
    # raw_validated state for this request.
    raw_sha256_before = sha256_of_file(raw_path)
    with sqlite3.connect(journal_path) as connection:
        connection.execute(
            "UPDATE requests SET state = 'raw_validated', raw_path = ?, "
            "raw_checksum = ?, raw_record_count = 21, raw_byte_count = ?, "
            "normalized_path = NULL, normalized_checksum = NULL, "
            "request_completed_at = NULL, failure_category = NULL, "
            "failure_message = NULL WHERE request_id = ?",
            (str(raw_path), raw_sha256_before, raw_path.stat().st_size, target_id),
        )
        connection.commit()
    plan = json.loads(
        (root / "data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
    )
    requests = [AcquisitionRequest.model_validate(item) for item in plan["requests"]]
    scope = RemainingRequestScope.model_validate_json(
        (root / "reports/data/execution/remaining_scope_24_f79f37a.scope.local.json").read_text(
            encoding="utf-8"
        )
    )
    raw_mtime_before = raw_path.stat().st_mtime_ns

    with RequestJournal(journal_path) as journal:
        target_before = journal.get(target_id)
        completed_before = journal.get(completed_id)
        assert target_before is not None
        assert target_before.state == "raw_validated"
        assert target_before.raw_path == str(raw_path)
        assert target_before.raw_checksum == raw_sha256_before
        assert target_before.raw_record_count == 21
        assert completed_before is not None
        for request_id in scope.remaining_request_ids:
            if request_id == target_id:
                continue
            entry = journal.get(request_id)
            assert entry is not None
            raw = tmp_path / "settled" / f"{request_id}.dbn"
            normalized = tmp_path / "settled" / f"{request_id}.parquet"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(request_id.encode())
            normalized.write_bytes(request_id.encode())
            quality = tmp_path / "reports/data/quality" / f"{request_id}.json"
            quality.parent.mkdir(parents=True, exist_ok=True)
            quality.write_text('{"status":"passed"}', encoding="utf-8")
            journal.connection.execute(
                "UPDATE requests SET state = 'quality_validated', raw_path = ?, "
                "raw_checksum = ?, raw_record_count = 1, normalized_path = ?, "
                "normalized_checksum = ? WHERE request_id = ?",
                (
                    str(raw),
                    sha256_of_file(raw),
                    str(normalized),
                    sha256_of_file(normalized),
                    request_id,
                ),
            )
        journal.connection.commit()

    lifecycle = data_module._PilotCliLifecycle(data_root=tmp_path)
    target_request = next(request for request in requests if request.request_id == target_id)
    with RequestJournal(journal_path) as journal:
        assert lifecycle.inspect(target_request, journal.get(target_id)) == (
            True,
            False,
            False,
            False,
        )

    paid_factory_calls = 0

    def fail_paid_factory() -> Any:
        nonlocal paid_factory_calls
        paid_factory_calls += 1
        raise AssertionError("raw-validated resume must not construct a paid provider")

    monkeypatch.setattr(
        PilotExecutionCoordinator,
        "validate_only",
        lambda *_args, **_kwargs: ValidationOnlyResult(
            ready_for_paid_execution=True,
            fresh_preflight_hash=plan["plan_hash"],
            estimated_total_cost="0",
            largest_request_cost="0",
        ),
    )

    class FailingLifecycle:
        inspect = lifecycle.inspect
        quality = lifecycle.quality

        def normalize(self, request: AcquisitionRequest, raw: RawAcquisitionResult) -> Any:
            raise ValueError("sanitized local normalization failure")

    common = {
        "requests": requests,
        "config": load_pilot_config(
            root / "configs/data/acquisition/pilot_january_2019.frozen_plan_v1.yaml"
        ),
        "plan_hash": plan["plan_hash"],
        "plan_bindings": plan["bindings"],
        "plan_metadata": data_module._pilot_plan_hash_metadata(plan),
        "authorization_path": tmp_path / "unused-authorization.json",
        "authorization_hash": "f" * 64,
        "portal_attestation_hash": "t" * 64,
        "confirm_plan_hash": plan["plan_hash"],
        "metadata_provider_factory": lambda: None,
        "paid_provider_factory": fail_paid_factory,
        "journal_factory": lambda: RequestJournal(journal_path),
        "now": datetime.now(UTC),
        "execution_scope": scope,
    }
    failed = PilotExecutionCoordinator().execute_paid(lifecycle=FailingLifecycle(), **common)
    with RequestJournal(journal_path) as journal:
        failed_entry = journal.get(target_id)
    assert failed.blocking_state == "local_processing_failure"
    assert failed.paid_provider_constructed is False
    assert failed.paid_request_calls == 0
    assert failed_entry is not None and failed_entry.state == "raw_validated"
    assert failed_entry.failure_category == "ValueError"
    assert failed_entry.failure_message == "sanitized local normalization failure"

    result = PilotExecutionCoordinator().execute_paid(lifecycle=lifecycle, **common)
    output = (
        tmp_path / "data/processed/pilot_january_2019/ARCX.PILLAR/ohlcv-1d" / f"{target_id}.parquet"
    )
    normalized = pd.read_parquet(output)
    with RequestJournal(journal_path) as journal:
        target_after = journal.get(target_id)
        completed_after = journal.get(completed_id)
    assert result.blocking_request is None
    assert result.paid_provider_constructed is False
    assert result.paid_request_calls == 0
    assert paid_factory_calls == 0
    assert target_after is not None and target_after.state == "quality_validated"
    assert completed_after == completed_before
    assert len(normalized) == 21
    assert normalized["raw_symbol"].unique().tolist() == ["SPY"]
    assert normalized["instrument_id"].unique().tolist() == [15144]
    assert normalized["source_request_id"].unique().tolist() == [target_id]
    assert sha256_of_file(raw_path) == raw_sha256_before
    assert raw_path.stat().st_mtime_ns == raw_mtime_before
