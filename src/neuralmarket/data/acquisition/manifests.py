"""Acquisition policy manifest hashing and offline plan/policy verification."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from neuralmarket.data.acquisition.contracts import AcquisitionPlanReport, AcquisitionPolicyManifest
from neuralmarket.data.errors import PlanValidationError
from neuralmarket.data.manifests import canonical_dumps

_HASH_EXCLUDED = ("manifest_hash", "generated_at")


def canonical_policy_hash(payload: dict[str, Any]) -> str:
    """Return the SHA-256 over canonical JSON of a policy payload minus volatile fields."""
    reduced = {k: v for k, v in payload.items() if k not in _HASH_EXCLUDED}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def finalize_policy_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the canonical manifest hash to a policy payload."""
    finalized = dict(payload)
    finalized["manifest_hash"] = canonical_policy_hash(payload)
    return finalized


def verify_policy_hash(payload: dict[str, Any]) -> None:
    """Raise if a policy manifest's stored hash does not match its canonical payload."""
    stored = payload.get("manifest_hash")
    if not isinstance(stored, str):
        raise PlanValidationError("Acquisition policy manifest is missing a string manifest_hash.")
    recomputed = canonical_policy_hash(payload)
    if stored != recomputed:
        raise PlanValidationError(
            f"Acquisition policy manifest hash mismatch: stored {stored}, recomputed {recomputed}."
        )


def parse_policy_manifest(payload: dict[str, Any]) -> AcquisitionPolicyManifest:
    """Validate a payload as an :class:`AcquisitionPolicyManifest`."""
    try:
        return AcquisitionPolicyManifest.model_validate(payload)
    except ValidationError as exc:
        raise PlanValidationError(f"Invalid acquisition policy manifest: {exc}") from exc


def parse_plan_report(payload: dict[str, Any]) -> AcquisitionPlanReport:
    """Validate a payload as an :class:`AcquisitionPlanReport`."""
    try:
        return AcquisitionPlanReport.model_validate(payload)
    except ValidationError as exc:
        raise PlanValidationError(f"Invalid acquisition plan report: {exc}") from exc


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file into a dictionary, raising :class:`PlanValidationError` on failure."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanValidationError(f"File not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanValidationError(f"Unable to read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlanValidationError(f"{path} must be a JSON object.")
    return raw


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write sorted UTF-8 JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".partial", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def verify_plan_and_policy(plan_payload: dict[str, Any], policy_payload: dict[str, Any]) -> None:
    """Cross-validate an acquisition plan report and policy manifest offline.

    Raises:
        PlanValidationError: If schemas, hashes, budget arithmetic, or
            plan/policy agreement fail.
    """
    verify_policy_hash(policy_payload)
    policy = parse_policy_manifest(policy_payload)
    plan = parse_plan_report(plan_payload)

    if policy.purchase_authorized or plan.budget_policy.purchase_authorized:
        raise PlanValidationError("purchase_authorized must remain false.")
    if not policy.download_guard_enabled:
        raise PlanValidationError("download_guard_enabled must remain true.")
    if (
        plan.download_attempts != 0
        or plan.downloaded_records != 0
        or plan.batch_jobs_submitted != 0
        or plan.live_connections_opened != 0
    ):
        raise PlanValidationError("Plan report indicates a nonzero acquisition attempt.")
    if plan.recommended_strategy_id != policy.recommended_strategy_id:
        raise PlanValidationError("Plan and policy manifest disagree on the recommended strategy.")
    if plan.recommendation_status != policy.recommendation_status:
        raise PlanValidationError("Plan and policy manifest disagree on the recommendation status.")
    if plan.source_manifest_hash != policy.source_manifest_hash:
        raise PlanValidationError("Plan and policy manifest disagree on the source-manifest hash.")
    if plan.split_manifest_hash != policy.split_manifest_hash:
        raise PlanValidationError("Plan and policy manifest disagree on the split-manifest hash.")
    if plan.config_hash != policy.config_hash:
        raise PlanValidationError("Plan and policy manifest disagree on the configuration hash.")

    budget = plan.budget_policy
    if Decimal(budget.maximum_project_spend_usd) + Decimal(
        budget.minimum_unspent_reserve_usd
    ) > Decimal(budget.available_credit_usd):
        raise PlanValidationError(
            "Budget invariant violated: project spend plus reserve exceeds available credit."
        )
    if Decimal(budget.maximum_development_quote_spend_usd) + Decimal(
        budget.minimum_final_test_quote_reserve_usd
    ) > Decimal(budget.maximum_project_spend_usd):
        raise PlanValidationError(
            "Budget invariant violated: development quote spend plus test reserve "
            "exceeds project spend cap."
        )
    if plan.pilot_plan.estimated_total_cost_usd and (
        Decimal(plan.pilot_plan.estimated_total_cost_usd)
        > Decimal(plan.pilot_plan.maximum_allowed_total_usd)
        and plan.pilot_plan.within_cap
    ):
        raise PlanValidationError("Pilot plan is marked within_cap but exceeds its own cap.")
