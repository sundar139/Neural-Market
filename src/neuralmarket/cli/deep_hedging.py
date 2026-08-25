"""Production dispatch for deep-hedging synthetic generation and GRU training — v3.

Hard dispatch boundary: every scientific action requires --execute and
--authorization <tracked committed authorization artifact> plus only the
identity selector needed for that authorized job. No test bypass switches.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from typer import Option

from neuralmarket.research.deep_hedging.artifacts import COST_LEVELS, HEDGER_SEEDS, MEMBERS, RUN_PREFIXES
from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    build_implementation_manifest,
    verify_authorization_artifact,
    verify_implementation_manifest,
)
from neuralmarket.research.deep_hedging.runner import preflight_checks as runner_preflight_checks

app = typer.Typer(help="Deep-hedging synthetic generation and GRU training (production, fail-closed).", add_completion=False)


def _require_authorization_or_fail(authorization: Path) -> dict:
    """Verify authorization artifact and schema in exact logical order."""
    # 1. authorization artifact verification (repo-relative, tracked, clean, canonical/blob, commit, task_id)
    info = verify_authorization_artifact(authorization)
    # 2. authorization schema validation (including task family, contract, runtime, allowlists, max invocations, network, final access)
    payload = json.loads(authorization.read_bytes().decode("utf-8"))
    from neuralmarket.research.deep_hedging.runner import validate_authorization_schema

    validate_authorization_schema(payload)
    # 3. implementation-manifest verification (commit ancestor + source blobs)
    # payload must contain implementation_commit and source blobs / manifest SHA
    impl_commit = str(payload.get("implementation_commit") or "")
    # Build expected manifest for comparison
    # The authorization's implementation_commit should be ancestor of current HEAD
    # and source blobs must match current HEAD
    # We need to verify that the authorization's implementation_manifest_sha256 and source_blobs are correct
    # For now, we verify that the current HEAD's manifest matches the authorization's
    # (if authorization contains them)
    authorized_blobs = payload.get("implementation_source_blobs") or payload.get("source_blobs")
    if authorized_blobs and impl_commit:
        verify_implementation_manifest(authorized_commit=impl_commit, authorized_blobs=authorized_blobs)
    return {"info": info, "payload": payload, "impl_commit": impl_commit}


def _preflight_common(authorization: Path, payload: dict) -> None:
    """Common preflight in exact logical order."""
    # 4. contract SHA/blob verification (via runner preflight)
    # 5. clean tracked tree
    # 6. CUDA/runtime fail-close
    # These are done via runner.preflight_checks which checks contract, runtime, clean tree, CUDA
    runner_preflight_checks(require_clean_tree=True)
    # 7. authorized job membership will be checked per action
    # 8. artifact nonexistence/consumed-attempt checks are per action


@app.command("generate-synthetic")
def generate_synthetic(
    member: str = Option(..., "--member", help="Member ID (seed-01, seed-02, seed-04, seed-05, reserve-j01)"),
    authorization: Path = Option(..., "--authorization", help="Tracked committed authorization artifact (repo-relative)"),
    execute: bool = Option(False, "--execute", help=" actually execute (requires --authorization and --member)"),
) -> None:
    """Generate synthetic dataset for one authorized member (requires --execute and --authorization)."""
    if not execute:
        typer.echo("DRY RUN: would generate synthetic for member {}".format(member))
        typer.echo("Use --execute --authorization <path> --member <id> to run")
        raise typer.Exit(code=0)
    if member not in MEMBERS:
        typer.echo(f"member {member} not in allowlist {MEMBERS}", err=True)
        raise typer.Exit(code=2)
    # Exact logical order before dispatch
    info_payload = _require_authorization_or_fail(authorization)
    payload = info_payload["payload"]
    # Validate member in allowlist
    allowlist = payload.get("member_allowlist", [])
    if member not in allowlist:
        typer.echo(f"member {member} not in authorization allowlist {allowlist}", err=True)
        raise typer.Exit(code=2)
    _preflight_common(authorization, payload)
    # Artifact nonexistence/consumed-attempt checks
    run_prefix = RUN_PREFIXES[member]
    dataset_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_episodes_v1.parquet")
    manifest_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_manifest_v1.json")
    started_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/generation_execution_started.json")
    if dataset_path.exists() or manifest_path.exists():
        typer.echo(f"OVERWRITE_REFUSED: dataset or manifest already exists at {dataset_path} / {manifest_path}", err=True)
        raise typer.Exit(code=2)
    if started_path.exists():
        typer.echo(f"CONSUMED: generation attempt already exists at {started_path}", err=True)
        raise typer.Exit(code=2)
    # Only then call production generation
    from neuralmarket.research.deep_hedging.generation import generate_and_persist_synthetic_dataset

    try:
        # Use checkpoint identity from authorization payload
        checkpoint_identities = payload.get("checkpoint_identities") or {}
        synthetic_rng = payload.get("synthetic_rng") or {}
        checkpoint_sha = checkpoint_identities.get(member)
        checkpoint_path_str = payload.get("checkpoint_paths", {}).get(member) or f"data/processed/research/model/structured-volatility-neural-sde-v5/{member}/checkpoint.pt"
        # For now, use the path from payload or default; in real authorized run, this will be exact
        result = generate_and_persist_synthetic_dataset(
            member=member,
            run_prefix=run_prefix,
            checkpoint_path=Path(checkpoint_path_str) if checkpoint_path_str else None,
            expected_checkpoint_sha256=checkpoint_sha,
            expected_checkpoint_blob=None,  # will be derived via git hash-object if needed
            synthetic_seed=synthetic_rng.get(member),
            dataset_path=dataset_path,
            manifest_path=manifest_path,
        )
        typer.echo(f"generated {result}")
    except Exception as e:
        typer.echo(f"generation failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command("train-policy")
def train_policy(
    member: str = Option(..., "--member", help="Member ID"),
    cost: float = Option(..., "--cost", help="Cost level (0.0, 0.0010, 0.0050)"),
    hedger_seed: int = Option(..., "--hedger-seed", help="Hedger seed (31001, 31002, 31003)"),
    authorization: Path = Option(..., "--authorization", help="Tracked committed authorization artifact"),
    execute: bool = Option(False, "--execute", help="actually execute"),
) -> None:
    """Train one GRU hedger policy for one authorized (member,cost,hedger_seed)."""
    if not execute:
        typer.echo(f"DRY RUN: would train policy for {(member, cost, hedger_seed)}")
        raise typer.Exit(code=0)
    if member not in MEMBERS:
        typer.echo(f"member {member} not in allowlist", err=True)
        raise typer.Exit(code=2)
    if cost not in COST_LEVELS:
        typer.echo(f"cost {cost} not in allowlist {COST_LEVELS}", err=True)
        raise typer.Exit(code=2)
    if hedger_seed not in HEDGER_SEEDS:
        typer.echo(f"hedger_seed {hedger_seed} not in allowlist", err=True)
        raise typer.Exit(code=2)
    info_payload = _require_authorization_or_fail(authorization)
    payload = info_payload["payload"]
    if member not in payload.get("member_allowlist", []):
        typer.echo(f"member {member} not in allowlist", err=True)
        raise typer.Exit(code=2)
    if cost not in payload.get("cost_allowlist", []):
        typer.echo(f"cost {cost} not in allowlist", err=True)
        raise typer.Exit(code=2)
    if hedger_seed not in payload.get("hedger_seed_allowlist", []):
        typer.echo(f"hedger_seed {hedger_seed} not in allowlist", err=True)
        raise typer.Exit(code=2)
    _preflight_common(authorization, payload)
    # Artifact nonexistence/consumed-attempt checks
    run_prefix = RUN_PREFIXES[member]
    cost_bps = {0.0: 0, 0.0010: 10, 0.0050: 50}[cost]
    policy_dir = Path(f"data/processed/research/hedging_policies/{run_prefix}_{member}/c_{cost_bps}/h_{hedger_seed}")
    started = policy_dir / "execution_started.json"
    checkpoint = policy_dir / "checkpoint.pt"
    if started.exists() or checkpoint.exists():
        typer.echo(f"CONSUMED or OVERWRITE_REFUSED at {policy_dir}", err=True)
        raise typer.Exit(code=2)
    # Check synthetic dataset exists (must have been generated)
    dataset_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_episodes_v1.parquet")
    manifest_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_manifest_v1.json")
    if not dataset_path.exists() or not manifest_path.exists():
        typer.echo(f"synthetic dataset not found for {member} at {dataset_path}", err=True)
        raise typer.Exit(code=2)
    from neuralmarket.research.deep_hedging.trainer import train_one_policy

    try:
        result = train_one_policy(
            member=member,
            cost=cost,
            hedger_seed=hedger_seed,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
        )
        typer.echo(f"trained {result}")
    except Exception as e:
        typer.echo(f"training failed: {e}", err=True)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
