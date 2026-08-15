"""Deterministic frozen research-development inventory.

Rolls the acquisition journal and scope dispositions up to the 499 canonical
scientific development requirements and seals a hash-bound inventory that
distinguishes quality_validated_paid, quality_validated_reused, unavailable,
and uncertain_billing at the canonical level. Sealed final-test dates are
rejected; missing observations are recorded, never synthesized.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from neuralmarket.data.acquisition.development import (
    DevelopmentPlan,
    DevelopmentRequest,
    load_development_plan,
    load_development_scope,
)
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentExecutionManifest,
    load_development_execution_manifest,
)
from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.calendar import compute_splits, session_dates
from neuralmarket.data.configuration import DataConfig, load_data_config
from neuralmarket.data.errors import CoverageError
from neuralmarket.data.manifests import canonical_dumps

ResearchDisposition = Literal[
    "quality_validated_paid",
    "quality_validated_reused",
    "unavailable",
    "uncertain_billing",
]

_INVENTORY_VERSION: Literal["research-development-inventory-v1"] = (
    "research-development-inventory-v1"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class ResearchRequirementEntry(BaseModel):
    """One canonical scientific requirement with its exact disposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    development_request_id: str
    development_request_hash: str
    dataset: str
    schema_name: str
    purpose: str
    expected_split: Literal["training", "validation"]
    session_date: str | None = None
    disposition: ResearchDisposition
    execution_request_ids: tuple[str, ...]
    raw_sha256s: tuple[str, ...]
    pilot_source_request_id: str | None = None
    reason: str

    @model_validator(mode="after")
    def _validate_identity(self) -> ResearchRequirementEntry:
        if len(self.execution_request_ids) != len(self.raw_sha256s):
            raise ValueError("execution identities and raw checksums must pair exactly")
        if self.disposition in {"quality_validated_reused", "unavailable"}:
            if self.execution_request_ids or self.raw_sha256s:
                raise ValueError("reused/unavailable entries carry no paid execution identity")
            if not self.pilot_source_request_id:
                raise ValueError("reused/unavailable entries require a pilot source identity")
        if self.disposition == "quality_validated_paid" and not self.execution_request_ids:
            raise ValueError("paid-validated entries require execution identities")
        return self


class ResearchCoverage(BaseModel):
    """Planned/available/missing session accounting by split."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    training_planned: int
    training_available: int
    training_missing: int
    validation_planned: int
    validation_available: int
    validation_missing: int
    missing_session_dates: tuple[str, ...]


class ResearchInventory(BaseModel):
    """Hash-bound frozen research-development dataset inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["research-development-inventory-v1"] = _INVENTORY_VERSION
    plan_hash: str
    execution_manifest_hash: str
    source_head: str
    requirements: tuple[ResearchRequirementEntry, ...]
    coverage: ResearchCoverage
    inventory_hash: str = ""

    @model_validator(mode="after")
    def _validate_inventory(self) -> ResearchInventory:
        ids = [entry.development_request_id for entry in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("research inventory contains duplicate requirement identities")
        if self.inventory_hash:
            expected = hashlib.sha256(
                canonical_dumps(
                    self.model_dump(mode="json", by_alias=True, exclude={"inventory_hash"})
                ).encode("utf-8")
            ).hexdigest()
            if self.inventory_hash != expected:
                raise ValueError("research inventory hash mismatch")
        return self


def _sealed_test_sessions(config: DataConfig) -> set[date]:
    """Return every final-test session date from the frozen split design."""
    sessions = session_dates(config.study.calendar, config.study.start_date, config.study.end_date)
    splits = compute_splits(config, sessions)
    if splits.test_start is None or splits.test_end is None:
        raise CoverageError("split design provides no final-test block")
    return set(session_dates(config.study.calendar, splits.test_start, splits.test_end))


def _verify_artifact(path_value: str | None, checksum: str | None, root: Path) -> None:
    if path_value is None or checksum is None:
        raise CoverageError("reused disposition lacks complete artifact evidence")
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = root / candidate
    if not candidate.is_file():
        raise CoverageError(f"reused artifact is missing: {path_value}")
    if _sha256_file(candidate) != checksum:
        raise CoverageError(f"reused artifact checksum mismatch: {path_value}")


def verify_fragment_parent_coverage(
    children: list[Any],
    parent_start: Any,
    parent_end_exclusive: Any,
) -> None:
    """Require fragment windows to tile the parent interval exactly.

    Sorted fragment starts must chain without gaps or overlaps from the parent
    start to the parent end_exclusive bound.
    """
    ordered = sorted(children, key=lambda item: item.start)
    cursor = parent_start
    for child in ordered:
        if child.start != cursor:
            raise CoverageError(
                f"fragment windows do not tile the parent exactly (gap or overlap) at {child.start}"
            )
        cursor = child.end_exclusive
    if cursor != parent_end_exclusive:
        raise CoverageError("fragment windows do not reach the parent end_exclusive bound")


def build_research_inventory(
    *,
    plan_path: Path,
    manifest_path: Path,
    scope_source_path: Path,
    journal_path: Path,
    config_path: Path,
    repository_root: Path,
    source_head: str,
) -> ResearchInventory:
    """Build and seal the deterministic research-development inventory.

    All inputs are read-only. The development journal must be terminal
    (quality_validated/uncertain_billing only) and pass an integrity check.
    """
    root = repository_root.resolve()
    plan: DevelopmentPlan = load_development_plan(plan_path)
    manifest: DevelopmentExecutionManifest = load_development_execution_manifest(manifest_path)
    scope = load_development_scope(scope_source_path, plan, repository_root=root)
    config = load_data_config(config_path)

    with sqlite3.connect(journal_path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise CoverageError(f"development journal integrity check failed: {integrity}")
    journal = RequestJournal(journal_path)
    journal_by_id = {entry.request_id: entry for entry in journal.all()}
    allowed_states = {"quality_validated", "uncertain_billing"}
    for journal_entry in journal_by_id.values():
        if journal_entry.state not in allowed_states:
            raise CoverageError(
                f"development journal is not terminal: {journal_entry.request_id} "
                f"state={journal_entry.state}"
            )

    sealed_sessions = _sealed_test_sessions(config)

    plan_by_id: dict[str, DevelopmentRequest] = {
        request.request_id: request for request in plan.requests
    }
    if len(plan_by_id) != len(plan.requests):
        raise CoverageError("development plan contains duplicate requirement identities")
    children_by_parent: dict[str, list[Any]] = {}
    for item in manifest.execution_requests:
        children_by_parent.setdefault(item.parent_request_id, []).append(item)

    reused_by_parent = {item.development_request_id: item for item in scope.reusable}
    unavailable_by_parent = {item.development_request_id: item for item in scope.unavailable}

    entries: list[ResearchRequirementEntry] = []
    for parent in plan.requests:
        if parent.expected_split not in {"training", "validation"}:
            raise CoverageError(
                f"canonical requirement outside development splits: {parent.request_id}"
            )
        if parent.session_date is not None and parent.session_date in sealed_sessions:
            raise CoverageError(
                f"sealed final-test session entered the research inventory: "
                f"{parent.request_id} {parent.session_date.isoformat()}"
            )
        if parent.request_id in reused_by_parent:
            disposition = reused_by_parent[parent.request_id]
            for artifact, checksum in (
                (disposition.raw_artifact_path, disposition.raw_checksum),
                (disposition.normalized_artifact_path, disposition.normalized_checksum),
            ):
                _verify_artifact(artifact, checksum, root)
            if (
                not disposition.quality_report_path
                or not (root / disposition.quality_report_path).is_file()
            ):
                raise CoverageError("reused disposition lacks quality report evidence")
            entries.append(
                ResearchRequirementEntry(
                    development_request_id=parent.request_id,
                    development_request_hash=parent.request_hash,
                    dataset=parent.dataset,
                    schema_name=parent.schema_name,
                    purpose=str(parent.purpose),
                    expected_split=parent.expected_split,
                    session_date=(parent.session_date.isoformat() if parent.session_date else None),
                    disposition="quality_validated_reused",
                    execution_request_ids=(),
                    raw_sha256s=(),
                    pilot_source_request_id=disposition.source_request_id,
                    reason="pilot quality_validated artifact reused",
                )
            )
            continue
        if parent.request_id in unavailable_by_parent:
            disposition = unavailable_by_parent[parent.request_id]
            entries.append(
                ResearchRequirementEntry(
                    development_request_id=parent.request_id,
                    development_request_hash=parent.request_hash,
                    dataset=parent.dataset,
                    schema_name=parent.schema_name,
                    purpose=str(parent.purpose),
                    expected_split=parent.expected_split,
                    session_date=(parent.session_date.isoformat() if parent.session_date else None),
                    disposition="unavailable",
                    execution_request_ids=(),
                    raw_sha256s=(),
                    pilot_source_request_id=disposition.source_request_id,
                    reason=f"pilot source state {disposition.source_state}",
                )
            )
            continue

        children = children_by_parent.get(parent.request_id)
        if not children:
            raise CoverageError(f"canonical requirement lacks a disposition: {parent.request_id}")
        child_states = [journal_by_id[child.execution_request_id].state for child in children]
        if any(state == "uncertain_billing" for state in child_states):
            research_disposition: ResearchDisposition = "uncertain_billing"
            reason = "one or more execution requests ended uncertain_billing"
        elif all(state == "quality_validated" for state in child_states):
            research_disposition = "quality_validated_paid"
            reason = "quality_validated paid acquisition"
        else:
            raise CoverageError(
                f"unexpected journal states for {parent.request_id}: {child_states}"
            )
        execution_ids: tuple[str, ...] = ()
        raw_sha256s: tuple[str, ...] = ()
        if research_disposition == "quality_validated_paid":
            ordered = sorted(children, key=lambda item: item.start)
            if len(ordered) > 1:
                verify_fragment_parent_coverage(ordered, parent.start, parent.end_exclusive)
            execution_ids = tuple(child.execution_request_id for child in ordered)
            raw_sha256s = tuple(
                str(journal_by_id[child.execution_request_id].raw_checksum) for child in ordered
            )
        entries.append(
            ResearchRequirementEntry(
                development_request_id=parent.request_id,
                development_request_hash=parent.request_hash,
                dataset=parent.dataset,
                schema_name=parent.schema_name,
                purpose=str(parent.purpose),
                expected_split=parent.expected_split,
                session_date=(parent.session_date.isoformat() if parent.session_date else None),
                disposition=research_disposition,
                execution_request_ids=execution_ids,
                raw_sha256s=raw_sha256s,
                pilot_source_request_id=None,
                reason=reason,
            )
        )

    if len(entries) != len(plan.requests):
        raise CoverageError("research inventory does not cover the canonical plan")

    available: set[str] = set()
    missing: list[str] = []
    counts: dict[tuple[str, str], Counter[str]] = {}
    for entry in entries:
        if entry.purpose == "strategy_b_closing_quote":
            split = entry.expected_split
            bucket = counts.setdefault((split, "cbbo"), Counter())
            bucket["planned"] += 1
            if entry.disposition in {"quality_validated_paid", "quality_validated_reused"}:
                bucket["available"] += 1
                available.add(entry.session_date or "")
            else:
                bucket["missing"] += 1
                missing.append(entry.session_date or "")
    del available

    def total(split: str, label: str) -> int:
        return int(counts.get((split, "cbbo"), Counter()).get(label, 0))

    coverage = ResearchCoverage(
        training_planned=total("training", "planned"),
        training_available=total("training", "available"),
        training_missing=total("training", "missing"),
        validation_planned=total("validation", "planned"),
        validation_available=total("validation", "available"),
        validation_missing=total("validation", "missing"),
        missing_session_dates=tuple(sorted(missing)),
    )

    inventory = ResearchInventory(
        plan_hash=plan.plan_hash,
        execution_manifest_hash=manifest.manifest_hash,
        source_head=source_head,
        requirements=tuple(entries),
        coverage=coverage,
    )
    inventory_hash = hashlib.sha256(
        canonical_dumps(
            inventory.model_dump(mode="json", by_alias=True, exclude={"inventory_hash"})
        ).encode("utf-8")
    ).hexdigest()
    return inventory.model_copy(update={"inventory_hash": inventory_hash})


def inventory_dispositions(inventory: ResearchInventory) -> dict[str, int]:
    """Return disposition counts for reporting."""
    return dict(Counter(entry.disposition for entry in inventory.requirements))


def catalog_availability(
    inventory: ResearchInventory,
) -> dict[str, dict[str, Any]]:
    """Return catalog/reference availability by split and schema."""
    report: dict[str, dict[str, Any]] = {}
    for entry in inventory.requirements:
        if entry.purpose == "strategy_b_closing_quote":
            continue
        key = f"{entry.expected_split}/{entry.schema_name}"
        report.setdefault(key, {"disposition": entry.disposition, "reason": entry.reason})
    return report


def write_research_inventory(path: Path, inventory: ResearchInventory) -> None:
    """Write the canonical tracked research inventory manifest."""
    path.write_text(
        canonical_dumps(inventory.model_dump(mode="json", by_alias=True, exclude_none=True)) + "\n",
        encoding="utf-8",
    )
