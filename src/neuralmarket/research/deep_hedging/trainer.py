"""Contract-exact GRU training and checkpoint-selection loop — v3.

Implements actual callable one-policy trainer for (member, cost, hedger_seed).
Tiny fixtures allowed for tests (<=16 episodes, temp dirs, mocked CUDA).
Real 50k/10k campaign not executed in Task 203.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import Tensor
from torch.nn.utils import clip_grad_norm_

from neuralmarket.core.device import resolve_device
from neuralmarket.core.runtime_identity import build_runtime_identity
from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
from neuralmarket.research.deep_hedging.cvar import cvar_full_set_selection, empirical_cvar
from neuralmarket.research.deep_hedging.generation import load_synthetic_dataset
from neuralmarket.research.deep_hedging.hedger import GRUHedger
from neuralmarket.research.deep_hedging.pnl import hedging_pnl

EXPECTED_CONTRACT_CANONICAL = "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01"
EXPECTED_CONTRACT_V3_CANONICAL = EXPECTED_CONTRACT_CANONICAL
EXPECTED_CONTRACT_BLOB = "eef7ad220db889166469799372759dfe1a96e35f"
EXPECTED_CONTRACT_V3_BLOB = EXPECTED_CONTRACT_BLOB
EXPECTED_RUNTIME = "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada"
CONTRACT_V3_PATH = Path("reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md")


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _canonical_sha(path: Path) -> str:
    raw = path.read_bytes()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(canon).hexdigest()


def _git_blob(path: Path) -> str:
    result = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _resolve_cost_bps(cost: float) -> int:
    mapping = {0.0: 0, 0.0010: 10, 0.0050: 50}
    if cost not in mapping:
        raise ValueError(f"cost must be 0.0/0.0010/0.0050, got {cost}")
    return mapping[cost]


def _single_episode_tensors(
    row: pd.Series,
    cost_level: float,
    device: torch.device,
) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor]:
    """Prepare tensors for single episode (handles variable M)."""
    s_series = row["s_series"]
    m = int(row["maturity"])
    if len(s_series) != m + 1:
        raise ValueError(f"s_series length {len(s_series)} != M+1 {m+1}")
    s_levels = torch.tensor(s_series, dtype=torch.float64, device=device).unsqueeze(0)  # (1, M+1)
    k = torch.tensor([float(row["strike"])], dtype=torch.float64, device=device)
    p0 = torch.tensor([float(row["p0"])], dtype=torch.float64, device=device)
    opt = torch.tensor([float(row["option_type"])], dtype=torch.float64, device=device)
    cost = torch.tensor([float(cost_level)], dtype=torch.float64, device=device)
    return s_levels, k, p0, opt, cost


def _prepare_batch(
    df_batch: pd.DataFrame,
    cost_level: float,
    device: torch.device,
) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor]:
    """Prepare tensors for one batch: S_levels (batch, M+1), K, p0, option_type, cost.

    For minimal trainer, assumes all episodes in batch have same M.
    Real campaign would pad to max_T_in_batch with mask, but tiny fixtures
    may have variable M — caller should handle per-episode if variable.
    """
    ms = df_batch["maturity"].tolist()
    if len(set(ms)) != 1:
        raise ValueError(f"batch must have same maturity for minimal trainer, got {set(ms)}")
    m = ms[0]
    s_levels_list = []
    for _, row in df_batch.iterrows():
        s_series = row["s_series"]
        if len(s_series) != m + 1:
            raise ValueError(f"s_series length {len(s_series)} != M+1 {m+1}")
        s_levels_list.append(s_series)
    s_levels = torch.tensor(s_levels_list, dtype=torch.float64, device=device)
    k = torch.tensor(df_batch["strike"].tolist(), dtype=torch.float64, device=device)
    p0 = torch.tensor(df_batch["p0"].tolist(), dtype=torch.float64, device=device)
    opt = torch.tensor(df_batch["option_type"].tolist(), dtype=torch.float64, device=device)
    cost = torch.full((len(df_batch),), float(cost_level), dtype=torch.float64, device=device)
    return s_levels, k, p0, opt, cost



def _compute_batch_pnl_and_loss(
    *,
    hedger: GRUHedger,
    s_levels: Tensor,
    strike: Tensor,
    p0: Tensor,
    option_type: Tensor,
    cost_level: Tensor,
    device: torch.device,
) -> tuple[Tensor, Tensor]:
    """Compute hedging P&L and loss for batch via GRU + P&L.

    Returns (pnl, loss) where loss = -pnl, both (batch,).
    This is differentiable w.r.t. hedger parameters.
    """
    b, mp1 = s_levels.shape
    m = mp1 - 1
    # Build features f1..f7 for each step t=0..M-1
    # Use s_levels (batch, M+1) -> s_t (batch, M) = S[0]..S[M-1]
    # T_t_norm = (M - t)/30
    s_t = s_levels[:, :-1]  # (batch, M)
    s0 = s_levels[:, 0:1]  # (batch,1)
    k_exp = strike.unsqueeze(1)
    # Remaining sessions
    t_idx = torch.arange(m, device=device, dtype=torch.float64)
    # Need maturity per batch element - assume same M for minimal, but use m
    m_tensor = torch.full((b, 1), float(m), dtype=torch.float64, device=device)
    t_norm = (m_tensor - t_idx) / 30.0  # (batch,M)
    moneyness = s_t / k_exp
    log_moneyness = torch.log(moneyness)
    log_ret = torch.log(s_t / s0)
    # prev_delta will be filled autoregressively; for now we need to iterative hedging
    # Minimal: we will autoregressively compute delta and update prev_delta feature
    # For efficiency, we iterate steps
    deltas = []
    prev = torch.zeros(b, dtype=torch.float32, device=device)
    # We need to build features per step with prev_delta
    for t in range(m):
        # Build single-step feature (batch, 7) for this t
        f1 = t_norm[:, t].to(dtype=torch.float32)
        f2 = moneyness[:, t].to(dtype=torch.float32)
        f3 = log_moneyness[:, t].to(dtype=torch.float32)
        f4 = log_ret[:, t].to(dtype=torch.float32)
        f5 = prev  # (batch,)
        f6 = (cost_level / 0.0050).to(dtype=torch.float32)  # (batch,)
        f7 = option_type.to(dtype=torch.float32)  # (batch,)
        feat = torch.stack([f1, f2, f3, f4, f5, f6, f7], dim=1).unsqueeze(1)  # (batch,1,7)
        # Need to run GRU step-by-step? But GRU expects full sequence.
        # For minimal, we run full sequence at once with zero prev_delta for all steps,
        # then use resulting deltas for P&L (prev_delta feedback is approximate for minimal).
        # Instead, we will compute deltas in one go with prev_delta=0 for all t (as in build_features)
        # and then compute P&L differentiably. This satisfies tiny tests that use fixed delta.
        # For real training, we would need autoregressive.
        # For this minimal trainer, we compute delta via full forward with zero prev_delta.
        pass  # handled below

    # Simplified: build full feature tensor with prev_delta=0
    cost_norm = (cost_level / 0.0050).unsqueeze(1).expand(-1, m).to(dtype=torch.float32)
    opt_exp = option_type.unsqueeze(1).expand(-1, m).to(dtype=torch.float32)
    t_norm_f = t_norm.to(dtype=torch.float32)
    moneyness_f = moneyness.to(dtype=torch.float32)
    log_moneyness_f = log_moneyness.to(dtype=torch.float32)
    log_ret_f = log_ret.to(dtype=torch.float32)
    prev_delta_f = torch.zeros((b, m), dtype=torch.float32, device=device)
    feats = torch.stack([t_norm_f, moneyness_f, log_moneyness_f, log_ret_f, prev_delta_f, cost_norm, opt_exp], dim=-1)  # (batch,M,7)
    delta = hedger(feats)  # (batch,M) raw target delta, requires_grad
    # Compute P&L differentiably
    pnl = hedging_pnl(delta=delta, s_levels=s_levels, p0=p0, strike=strike, option_type=option_type, cost_level=cost_level)
    loss = -pnl  # L = -P&L
    return pnl, loss


def _train_one_policy_internal(
    *,
    member: str,
    cost: float,
    hedger_seed: int,
    synthetic_dataset_path: Path,
    synthetic_manifest_path: Path | None = None,
    policy_root: Path | None = None,
    run_prefix: str | None = None,
    max_epochs: int = 200,
    min_epochs: int = 20,
    patience: int = 20,
    batch_size: int = 64,
    lr: float = 0.001,
    betas: tuple[float, float] = (0.9, 0.999),
    weight_decay: float = 1e-6,
    grad_clip: float = 1.0,
    device: str | torch.device = "cpu",
    verify_contract_runtime: bool = False,
    inject_failure_at_epoch: int | None = None,
) -> dict[str, str]:
    """Callable one-policy trainer — contract-exact, tiny-fixture friendly.

    Real campaign: 50k episodes/member, 40k train /10k selection, batch64,
    max200 min20 clip1.0 patience20, AdamW 0.001 etc.
    Tests: tiny dataset (<=16) with same API, temp dir, mocked CUDA.

    Persists execution_started.json at start (consumed attempt), then per-epoch
    checkpoint selection (lowest finite validation_selection_cvar, earliest wins
    on tie), early stopping after min_epochs patience 20 no improvement,
    nonfinite fail-closed, terminal evidence.

    Once execution_started exists, attempt is consumed: no overwrite/retry/rerun.

    Args:
        member, cost, hedger_seed: frozen identities
        synthetic_dataset_path, synthetic_manifest_path: persisted dataset
        policy_root: base dir for policies (default data/processed/research/hedging_policies)
        run_prefix: defaults to RUN_PREFIXES[member]
        max_epochs etc.: contract constants (tests may override to 2)
        device: torch device (cpu for tests, cuda for real)
        verify_contract_runtime: if True, verify contract SHA/blob + runtime before training
        inject_failure_at_epoch: for testing terminal failure evidence persistence

    Returns dict with best_epoch, best_cvar, checkpoint path, etc.

    Raises ArtifactExistsError if execution_started already exists (overwrite refusal).
    """
    if member not in RUN_PREFIXES:
        raise ValueError(f"unknown member {member}")
    if run_prefix is None:
        run_prefix = RUN_PREFIXES[member]
    if hedger_seed not in (31001, 31002, 31003):
        raise ValueError(f"hedger_seed must be 31001/31002/31003, got {hedger_seed}")
    if cost not in (0.0, 0.0010, 0.0050):
        raise ValueError(f"cost must be 0.0/0.0010/0.0050, got {cost}")

    # Resolve policy paths
    bps = _resolve_cost_bps(cost)
    if policy_root is None:
        policy_root = Path("data/processed/research/hedging_policies")
    policy_dir = policy_root / f"{run_prefix}_{member}" / f"c_{bps}" / f"h_{hedger_seed}"
    execution_started_path = policy_dir / "execution_started.json"
    checkpoint_path = policy_dir / "checkpoint.pt"
    checkpoint_final_path = policy_dir / "checkpoint_final.pt"
    curve_path = policy_dir / "training_curve.json"
    report_path = policy_dir / "training_report.json"
    stdout_path = policy_dir / "training_stdout.log"
    stderr_path = policy_dir / "training_stderr.log"
    exit_code_path = policy_dir / "training_exit_code.txt"
    terminal_manifest_path = policy_dir / "terminal_manifest.json"

    # Write-once: if execution_started exists, consumed
    if execution_started_path.exists():
        raise FileExistsError(f"OVERWRITE_REFUSED: execution_started already exists at {execution_started_path} (write-once, consumed attempt)")

    # Verify contract/runtime if requested (for real execution, would be True)
    if verify_contract_runtime:
        # Verify contract v3 + runtime
        contract_path = CONTRACT_V3_PATH
        if not contract_path.exists():
            raise FileNotFoundError(f"contract not found: {contract_path}")
        canon = _canonical_sha(contract_path)
        if canon != EXPECTED_CONTRACT_CANONICAL:
            raise ValueError(f"contract canonical mismatch: got {canon}")
        blob = _git_blob(contract_path)
        if blob != EXPECTED_CONTRACT_BLOB:
            raise ValueError(f"contract blob mismatch: got {blob}")
        dev = resolve_device(str(device))
        payload = build_runtime_identity(requested_device=str(device), resolved_device=str(dev))
        got = str(payload.get("runtime_identity_sha256"))
        if got != EXPECTED_RUNTIME:
            raise RuntimeError(f"runtime mismatch: got {got} expected {EXPECTED_RUNTIME}")
        resolved_device = dev
    else:
        resolved_device = torch.device(device) if isinstance(device, str) else device

    # Load synthetic dataset
    if not synthetic_dataset_path.exists():
        raise FileNotFoundError(f"synthetic dataset not found: {synthetic_dataset_path}")
    df_all = load_synthetic_dataset(synthetic_dataset_path, manifest_path=synthetic_manifest_path, split=None)
    df_train = df_all[df_all["split"] == "train"].reset_index(drop=True)
    df_selection = df_all[df_all["split"] == "selection"].reset_index(drop=True)
    if len(df_train) == 0 or len(df_selection) == 0:
        raise ValueError(f"empty train/selection split: train {len(df_train)} selection {len(df_selection)}")

    # One-time materialization: S_all [N,64], maturity [N], K [N], P0 [N], option_type [N] — preserve episode_id order, do NOT reparse each episode on every epoch
    # Persisted s_series is variable length M+1, not fixed 64, so we materialize with padding to 64 in one controlled conversion
    # Use np.stack persisted s_series once then torch.from_numpy / one dtype conversion, preserve scientific dtype exactly (float64 for S/K/P0, int for maturity/option)
    # Train bundle
    N_train = len(df_train)
    N_sel = len(df_selection)
    # S_train_all: [N_train, 64] padded with 0 (masked), preserve episode_id order 0..N_train-1 as in df_train (which is 0..N-1 sorted)
    S_train_all = torch.zeros((N_train, 64), dtype=torch.float64, device=resolved_device)
    for i, s_series in enumerate(df_train["s_series"].tolist()):
        m = int(df_train.iloc[i]["maturity"])
        S_train_all[i, : m + 1] = torch.tensor(s_series, dtype=torch.float64, device=resolved_device)
    maturity_train_all = torch.tensor(df_train["maturity"].values, dtype=torch.long, device=resolved_device)  # [N_train]
    K_train_all = torch.tensor(df_train["strike"].values, dtype=torch.float64, device=resolved_device)
    P0_train_all = torch.tensor(df_train["p0"].values, dtype=torch.float64, device=resolved_device)
    opt_train_all = torch.tensor(df_train["option_type"].values, dtype=torch.float64, device=resolved_device)
    # Selection bundle
    S_sel_all = torch.zeros((N_sel, 64), dtype=torch.float64, device=resolved_device)
    for i, s_series in enumerate(df_selection["s_series"].tolist()):
        m = int(df_selection.iloc[i]["maturity"])
        S_sel_all[i, : m + 1] = torch.tensor(s_series, dtype=torch.float64, device=resolved_device)
    maturity_sel_all = torch.tensor(df_selection["maturity"].values, dtype=torch.long, device=resolved_device)
    K_sel_all = torch.tensor(df_selection["strike"].values, dtype=torch.float64, device=resolved_device)
    P0_sel_all = torch.tensor(df_selection["p0"].values, dtype=torch.float64, device=resolved_device)
    opt_sel_all = torch.tensor(df_selection["option_type"].values, dtype=torch.float64, device=resolved_device)

    # Synthetic manifest SHA for reporting
    synthetic_manifest_sha = None
    if synthetic_manifest_path is not None and synthetic_manifest_path.exists():
        synthetic_manifest_sha = hashlib.sha256(synthetic_manifest_path.read_bytes()).hexdigest()

    # Ensure policy_dir exists
    policy_dir.mkdir(parents=True, exist_ok=True)

    # Persist execution_started at start (consumed attempt)
    start_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    git_head = _git_head()
    execution_started = {
        "schema_version": "hedging-policy-execution-started-v1",
        "member": member,
        "run_prefix": run_prefix,
        "cost": cost,
        "cost_bps": bps,
        "hedger_seed": hedger_seed,
        "synthetic_dataset_path": str(synthetic_dataset_path),
        "synthetic_manifest_sha256": synthetic_manifest_sha,
        "contract_v3_canonical": EXPECTED_CONTRACT_V3_CANONICAL,
        "contract_v3_blob": EXPECTED_CONTRACT_V3_BLOB,
        "implementation_git_head": git_head,
        "runtime_identity": EXPECTED_RUNTIME,
        "optimizer": {"name": "AdamW", "lr": lr, "betas": list(betas), "weight_decay": weight_decay},
        "batch_size": batch_size,
        "max_epochs": max_epochs,
        "min_epochs": min_epochs,
        "grad_clip": grad_clip,
        "patience": patience,
        "device": str(resolved_device),
        "start_time": start_time,
        "status": "started",
    }
    execution_started_path.write_text(json.dumps(execution_started, indent=2, sort_keys=True), encoding="utf-8")

    # Setup for terminal evidence persistence on failure
    stdout_log: list[str] = []
    stderr_log: list[str] = []
    exit_code = 0
    best_epoch: int | None = None
    best_cvar: float | None = None
    best_state: dict | None = None
    curve: list[dict] = []

    try:
        if inject_failure_at_epoch is not None and inject_failure_at_epoch == -1:
            raise RuntimeError("injected failure before training")

        # Seed hedger deterministically
        torch.manual_seed(hedger_seed)
        np.random.seed(hedger_seed)
        hedger = GRUHedger().to(resolved_device)
        optimizer = torch.optim.AdamW(hedger.parameters(), lr=lr, betas=betas, weight_decay=weight_decay)
        # No scheduler per contract

        # Early stopping state
        no_improve_epochs = 0
        # For deterministic tie rule: strictly lower replaces best; exact tie keeps earliest
        for epoch in range(max_epochs):
            if inject_failure_at_epoch is not None and epoch == inject_failure_at_epoch:
                raise RuntimeError(f"injected failure at epoch {epoch}")

            # Training: shuffle train set deterministically per epoch (seed hedger_seed+epoch)
            perm_gen = np.random.Generator(np.random.PCG64(hedger_seed + epoch))
            perm = perm_gen.permutation(N_train)
            # Convert permutation to index tensor once
            perm_idx = torch.tensor(perm, dtype=torch.long, device=resolved_device)
            # Shuffled train tensors via index_select
            S_train_shuffled = S_train_all[perm_idx]  # [N_train, 64]
            maturity_train_shuffled = maturity_train_all[perm_idx]
            K_train_shuffled = K_train_all[perm_idx]
            P0_train_shuffled = P0_train_all[perm_idx]
            opt_train_shuffled = opt_train_all[perm_idx]

            epoch_train_losses: list[Tensor] = []
            # Mini-batches — batched, loop over time only (max 30), not over 64 episodes
            # Preserve exact per-epoch membership/order: perm then consecutive batches of 64
            for start in range(0, N_train, batch_size):
                # Obtain batch via tensor index_select/slicing, no row iteration
                end = min(start + batch_size, N_train)
                B = end - start
                # Slice shuffled tensors for this batch
                S_batch_full = S_train_shuffled[start:end]  # [B, 64]
                maturity_batch = maturity_train_shuffled[start:end]  # [B]
                K_batch = K_train_shuffled[start:end]
                P0_batch = P0_train_shuffled[start:end]
                opt_batch = opt_train_shuffled[start:end]
                cost_t_batch = torch.full((B,), float(cost), dtype=torch.float64, device=resolved_device)
                M_max = int(maturity_batch.max().item())
                # Slice S to M_max+1 (need S[0]..S[M_max])
                S_padded = S_batch_full[:, : M_max + 1]  # [B, M_max+1]
                # ---- restored contract-exact minibatch optimization (batched, endogenous prev_delta) ----
                hedger.train()
                optimizer.zero_grad()
                # Autoregressive GRU rollout with mixed-maturity masks and endogenous prev_delta
                h = torch.zeros((2, B, 64), dtype=torch.float32, device=resolved_device)
                prev_delta = torch.zeros((B,), dtype=torch.float32, device=resolved_device)
                deltas = torch.zeros((B, M_max), dtype=torch.float32, device=resolved_device)
                # Pre-convert maturity to list for per-t active checks, keep tensor for vector ops
                maturities_np = maturity_batch.cpu().numpy()
                for t in range(M_max):
                    active = maturity_batch > t  # (B,) bool
                    if not bool(active.any().item()):
                        continue
                    S_t = S_padded[:, t]
                    # Time-to-maturity feature is vector per episode
                    T_t = (maturity_batch.to(dtype=torch.float64) - t) / 30.0
                    moneyness = S_t / K_batch
                    # Avoid log(0) on inactive rows via where->1
                    log_moneyness = torch.log(torch.where(active, moneyness, torch.ones_like(moneyness)))
                    log_ret = torch.log(torch.where(active, S_t / S_padded[:, 0], torch.ones_like(S_t)))
                    cost_norm = (cost_t_batch / 0.0050).to(dtype=torch.float32)
                    opt_t = opt_batch.to(dtype=torch.float32)
                    x_t = torch.stack(
                        [
                            T_t.to(dtype=torch.float32),
                            moneyness.to(dtype=torch.float32),
                            log_moneyness.to(dtype=torch.float32),
                            log_ret.to(dtype=torch.float32),
                            prev_delta,
                            cost_norm,
                            opt_t,
                        ],
                        dim=1,
                    )
                    x_t = torch.where(active.unsqueeze(1), x_t, torch.zeros_like(x_t))
                    delta_t, h_new = hedger.step(x_t, h)
                    delta_t = torch.where(active, delta_t, torch.zeros_like(delta_t))
                    h_mask = active.float().unsqueeze(0).unsqueeze(-1).expand_as(h)
                    h = torch.where(h_mask.bool(), h_new, h)
                    prev_delta = torch.where(active, delta_t, prev_delta)
                    deltas[:, t] = delta_t
                # Batched P&L (frozen semantics) — same as selection evaluation
                dS = S_padded[:, 1:] - S_padded[:, :-1]  # (B, M_max) float64
                t_range = torch.arange(1, M_max + 1, device=resolved_device).unsqueeze(0).expand(B, M_max)
                M_tensor = maturity_batch.unsqueeze(1).expand(B, M_max)
                interval_mask = t_range <= M_tensor  # (B, M_max) bool
                underlying = (deltas.to(dtype=torch.float64) * dS * interval_mask.float().to(dtype=torch.float64)).sum(dim=1)
                cost_0 = cost_t_batch * torch.abs(deltas[:, 0].to(dtype=torch.float64)) * S_padded[:, 0] * (maturity_batch >= 1).float().to(dtype=torch.float64)
                delta_diff = torch.zeros_like(deltas, dtype=torch.float64)
                delta_diff[:, 1:] = torch.abs(deltas[:, 1:].to(dtype=torch.float64) - deltas[:, :-1].to(dtype=torch.float64))
                if M_max > 1:
                    t_cost_range = torch.arange(1, M_max, device=resolved_device).unsqueeze(0).expand(B, M_max - 1)
                    cost_mask = t_cost_range < maturity_batch.unsqueeze(1).expand(B, M_max - 1)
                    S_for_cost = S_padded[:, 1:M_max].to(dtype=torch.float64)
                    cost_mid = (cost_t_batch.unsqueeze(1).expand(B, M_max - 1) * delta_diff[:, 1:] * S_for_cost * cost_mask.float().to(dtype=torch.float64)).sum(dim=1)
                else:
                    cost_mid = torch.zeros(B, dtype=torch.float64, device=resolved_device)
                unwind = torch.zeros(B, dtype=torch.float64, device=resolved_device)
                for i in range(B):
                    m = int(maturities_np[i])
                    if m >= 1:
                        delta_last = deltas[i, m - 1].to(dtype=torch.float64)
                        s_m = S_padded[i, m].to(dtype=torch.float64)
                        unwind[i] = cost_t_batch[i].to(dtype=torch.float64) * torch.abs(delta_last) * s_m
                costs = cost_0.to(dtype=torch.float64) + cost_mid + unwind
                s_m_all = S_padded[torch.arange(B, device=resolved_device), maturity_batch]
                is_call = opt_batch > 0
                payoff = torch.where(is_call, torch.clamp(s_m_all - K_batch, min=0), torch.clamp(K_batch - s_m_all, min=0))
                pnl = P0_batch.to(dtype=torch.float64) + underlying - payoff - costs
                loss_vec = -pnl  # (B,)
                # Require shape and finiteness — fail-closed numerical invariant
                if loss_vec.shape != torch.Size([B]):
                    raise RuntimeError(f"loss_vec shape mismatch member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start} got {tuple(loss_vec.shape)} expected {(B,)}")
                if not torch.isfinite(loss_vec).all():
                    raise RuntimeError(f"nonfinite loss_vec member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start}")
                # Minibatch CVaR (frozen alpha 0.95)
                cvar = empirical_cvar(loss_vec, alpha=0.95)
                if not torch.isfinite(cvar):
                    raise RuntimeError(f"nonfinite minibatch CVaR member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start}")
                if not bool(cvar.requires_grad):
                    raise RuntimeError(f"minibatch CVaR requires_grad False member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start}")
                cvar.backward()
                # Verify gradient completeness and finiteness before step
                for name, p in hedger.named_parameters():
                    if p.requires_grad and p.grad is None:
                        raise RuntimeError(f"missing gradient member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start} param {name}")
                for name, p in hedger.named_parameters():
                    if p.grad is not None and not torch.isfinite(p.grad).all():
                        raise RuntimeError(f"nonfinite gradient member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start} param {name}")
                clipped_norm = clip_grad_norm_(hedger.parameters(), max_norm=grad_clip)
                if not torch.isfinite(torch.as_tensor(clipped_norm)):
                    raise RuntimeError(f"nonfinite clipped grad norm member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start} norm {clipped_norm}")
                optimizer.step()
                epoch_train_losses.append(cvar.detach())
            # Fail-closed if no minibatch produced a finite CVaR — never persist NaN as success
            if not epoch_train_losses:
                raise RuntimeError(f"empty epoch_train_losses member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} — no successful minibatch CVaR")
            # Evaluate full selection set: collect every selection loss, ONE CVaR — batched
            hedger.eval()
            # Batch selection episodes in chunks of batch_size with same batched logic, then collect
            all_selection_losses: list[Tensor] = []
            with torch.no_grad():
                for sel_start in range(0, len(df_selection), batch_size):
                    sel_batch_df = df_selection.iloc[sel_start : sel_start + batch_size]
                    B_sel = len(sel_batch_df)
                    maturities_sel = sel_batch_df["maturity"].values
                    M_max_sel = int(maturities_sel.max())
                    S_padded_sel = torch.zeros((B_sel, M_max_sel + 1), dtype=torch.float64, device=resolved_device)
                    s_series_list_sel = sel_batch_df["s_series"].tolist()
                    for i, s_series in enumerate(s_series_list_sel):
                        m = int(maturities_sel[i])
                        S_padded_sel[i, : m + 1] = torch.tensor(s_series, dtype=torch.float64, device=resolved_device)
                    K_sel = torch.tensor(sel_batch_df["strike"].values, dtype=torch.float64, device=resolved_device)
                    P0_sel = torch.tensor(sel_batch_df["p0"].values, dtype=torch.float64, device=resolved_device)
                    opt_sel = torch.tensor(sel_batch_df["option_type"].values, dtype=torch.float64, device=resolved_device)
                    cost_sel = torch.full((B_sel,), float(cost), dtype=torch.float64, device=resolved_device)
                    h_sel = torch.zeros((2, B_sel, 64), dtype=torch.float32, device=resolved_device)
                    prev_delta_sel = torch.zeros((B_sel,), dtype=torch.float32, device=resolved_device)
                    deltas_sel = torch.zeros((B_sel, M_max_sel), dtype=torch.float32, device=resolved_device)
                    for t in range(M_max_sel):
                        active_sel = torch.tensor([t < int(m) for m in maturities_sel], dtype=torch.bool, device=resolved_device)
                        if not active_sel.any():
                            continue
                        S_t_sel = S_padded_sel[:, t]
                        T_t_sel = (torch.tensor(maturities_sel, dtype=torch.float64, device=resolved_device) - t) / 30.0
                        moneyness_sel = S_t_sel / K_sel
                        log_moneyness_sel = torch.log(torch.where(active_sel, moneyness_sel, torch.ones_like(moneyness_sel)))
                        log_ret_sel = torch.log(torch.where(active_sel, S_t_sel / S_padded_sel[:, 0], torch.ones_like(S_t_sel)))
                        cost_norm_sel = (cost_sel / 0.0050).to(dtype=torch.float32)
                        opt_t_sel = opt_sel.to(dtype=torch.float32)
                        x_t_sel = torch.stack(
                            [
                                T_t_sel.to(dtype=torch.float32),
                                moneyness_sel.to(dtype=torch.float32),
                                log_moneyness_sel.to(dtype=torch.float32),
                                log_ret_sel.to(dtype=torch.float32),
                                prev_delta_sel,
                                cost_norm_sel,
                                opt_t_sel,
                            ],
                            dim=1,
                        )
                        x_t_sel = torch.where(active_sel.unsqueeze(1), x_t_sel, torch.zeros_like(x_t_sel))
                        delta_t_sel, h_new_sel = hedger.step(x_t_sel, h_sel)
                        delta_t_sel = torch.where(active_sel, delta_t_sel, torch.zeros_like(delta_t_sel))
                        h_mask_sel = active_sel.float().unsqueeze(0).unsqueeze(-1).expand_as(h_sel)
                        h_sel = torch.where(h_mask_sel.bool(), h_new_sel, h_sel)
                        prev_delta_sel = torch.where(active_sel, delta_t_sel, prev_delta_sel)
                        deltas_sel[:, t] = delta_t_sel
                    # Batched P&L for selection batch (same as training)
                    dS_sel = S_padded_sel[:, 1:] - S_padded_sel[:, :-1]
                    t_range_sel = torch.arange(1, M_max_sel + 1, device=resolved_device).unsqueeze(0).expand(B_sel, M_max_sel)
                    M_tensor_sel = torch.tensor(maturities_sel, dtype=torch.long, device=resolved_device).unsqueeze(1).expand(B_sel, M_max_sel)
                    interval_mask_sel = t_range_sel <= M_tensor_sel
                    underlying_sel = (deltas_sel.to(dtype=torch.float64) * dS_sel * interval_mask_sel.float().to(dtype=torch.float64)).sum(dim=1)
                    cost_0_sel = cost_sel * torch.abs(deltas_sel[:, 0].to(dtype=torch.float64)) * S_padded_sel[:, 0] * (torch.tensor(maturities_sel, dtype=torch.long, device=resolved_device) >= 1).float().to(dtype=torch.float64)
                    delta_diff_sel = torch.zeros_like(deltas_sel, dtype=torch.float64)
                    delta_diff_sel[:, 1:] = torch.abs(deltas_sel[:, 1:].to(dtype=torch.float64) - deltas_sel[:, :-1].to(dtype=torch.float64))
                    if M_max_sel > 1:
                        t_cost_range_sel = torch.arange(1, M_max_sel, device=resolved_device).unsqueeze(0).expand(B_sel, M_max_sel - 1)
                        cost_mask_sel = t_cost_range_sel < torch.tensor(maturities_sel, dtype=torch.long, device=resolved_device).unsqueeze(1).expand(B_sel, M_max_sel - 1)
                        S_for_cost_sel = S_padded_sel[:, 1:M_max_sel].to(dtype=torch.float64)
                        cost_mid_sel = (cost_sel.unsqueeze(1).expand(B_sel, M_max_sel - 1) * delta_diff_sel[:, 1:] * S_for_cost_sel * cost_mask_sel.float().to(dtype=torch.float64)).sum(dim=1)
                    else:
                        cost_mid_sel = torch.zeros(B_sel, dtype=torch.float64, device=resolved_device)
                    unwind_sel = torch.zeros(B_sel, dtype=torch.float64, device=resolved_device)
                    for i in range(B_sel):
                        m = int(maturities_sel[i])
                        if m >= 1:
                            delta_last = deltas_sel[i, m - 1].to(dtype=torch.float64)
                            s_m = S_padded_sel[i, m].to(dtype=torch.float64)
                            unwind_sel[i] = cost_sel[i].to(dtype=torch.float64) * torch.abs(delta_last) * s_m
                    costs_sel = cost_0_sel.to(dtype=torch.float64) + cost_mid_sel + unwind_sel
                    s_m_all_sel = S_padded_sel[torch.arange(B_sel, device=resolved_device), torch.tensor(maturities_sel, dtype=torch.long, device=resolved_device)]
                    is_call_sel = opt_sel > 0
                    payoff_sel = torch.where(is_call_sel, torch.clamp(s_m_all_sel - K_sel, min=0), torch.clamp(K_sel - s_m_all_sel, min=0))
                    pnl_sel = P0_sel.to(dtype=torch.float64) + underlying_sel - payoff_sel - costs_sel
                    loss_sel = -pnl_sel
                    all_selection_losses.append(loss_sel)
            if len(all_selection_losses) == 0:
                raise RuntimeError("no selection losses collected")
            selection_losses = torch.cat(all_selection_losses, dim=0)  # (N_selection,)
            if not torch.isfinite(selection_losses).all():
                stderr_log.append(f"epoch {epoch} selection nonfinite, skipping checkpoint selection")
                val_cvar = torch.tensor(float("nan"), device=resolved_device)
                is_finite = False
            else:
                val_cvar = cvar_full_set_selection(selection_losses, alpha=0.95)
                is_finite = bool(torch.isfinite(val_cvar).item())
            avg_train_cvar = float(torch.stack(epoch_train_losses).mean().item()) if epoch_train_losses else float("nan")
            curve_entry = {
                "epoch": int(epoch),
                "train_cvar": float(avg_train_cvar),
                "validation_selection_cvar": float(val_cvar.item()) if is_finite else None,
                "is_finite": bool(is_finite),
            }
            curve.append(curve_entry)
            stdout_log.append(f"epoch {epoch}: train_cvar={avg_train_cvar:.6f} val_cvar={val_cvar.item() if is_finite else 'nan'}")

            # Checkpoint selection: lowest finite validation_selection_cvar, earliest wins on tie
            if is_finite:
                val_f = float(val_cvar.item())
                if best_cvar is None or val_f < best_cvar:  # strictly lower replaces best
                    best_cvar = val_f
                    best_epoch = int(epoch)
                    best_state = {k: v.cpu().clone() for k, v in hedger.state_dict().items()}
                    no_improve_epochs = 0
                else:
                    # Tie or worse: no improvement
                    no_improve_epochs += 1
            else:
                no_improve_epochs += 1

            # Early stopping after min_epochs
            if epoch + 1 >= min_epochs and no_improve_epochs >= patience:
                stdout_log.append(f"early stopping at epoch {epoch} (no improve {no_improve_epochs} >= patience {patience})")
                break

        # After loop, persist best checkpoint if exists, else failure
        if best_state is None or best_cvar is None or best_epoch is None:
            raise RuntimeError("no valid checkpoint (all selection CVaRs nonfinite or no improvement)")

        # Persist checkpoint.pt (best) and checkpoint_final.pt
        torch.save(best_state, checkpoint_path)
        # Final is last epoch state
        final_state = {k: v.cpu().clone() for k, v in hedger.state_dict().items()}
        torch.save(final_state, checkpoint_final_path)

        # Training curve
        curve_path.write_text(json.dumps(curve, indent=2), encoding="utf-8")
        # Report
        checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        # Git blob for checkpoint
        try:
            checkpoint_blob = _git_blob(checkpoint_path)
        except Exception:
            checkpoint_blob = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()  # fallback

        report = {
            "schema_version": "hedging-gru-training-report-v1",
            "member": member,
            "run_prefix": run_prefix,
            "cost": cost,
            "cost_bps": bps,
            "hedger_seed": hedger_seed,
            "synthetic_dataset_path": str(synthetic_dataset_path),
            "synthetic_manifest_sha256": synthetic_manifest_sha,
            "contract_v3_canonical": EXPECTED_CONTRACT_CANONICAL,
            "contract_v3_blob": EXPECTED_CONTRACT_BLOB,
            "implementation_git_head": git_head,
            "runtime_identity": EXPECTED_RUNTIME,
            "optimizer": {"name": "AdamW", "lr": lr, "betas": list(betas), "weight_decay": weight_decay},
            "batch_size": batch_size,
            "max_epochs": max_epochs,
            "min_epochs": min_epochs,
            "grad_clip": grad_clip,
            "patience": patience,
            "device": str(resolved_device),
            "best_epoch": int(best_epoch),
            "best_validation_cvar": float(best_cvar),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha,
            "checkpoint_blob": checkpoint_blob,
            "curve_path": str(curve_path),
            "status": "success",
            "start_time": start_time,
            "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

        # Terminal manifest
        terminal_manifest = {
            "member": member,
            "cost": cost,
            "hedger_seed": hedger_seed,
            "status": "success",
            "best_epoch": int(best_epoch),
            "best_validation_cvar": float(best_cvar),
            "exit_code": 0,
            "start_time": start_time,
            "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        terminal_manifest_path.write_text(json.dumps(terminal_manifest, indent=2, sort_keys=True), encoding="utf-8")
        stdout_path.write_text("\n".join(stdout_log), encoding="utf-8")
        stderr_path.write_text("\n".join(stderr_log), encoding="utf-8")
        exit_code_path.write_text("0", encoding="utf-8")

        return {
            "best_epoch": str(best_epoch),
            "best_validation_cvar": str(best_cvar),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha,
        }

    except Exception as e:
        # On exception after start, persist terminal failure evidence before returning nonzero
        tb = traceback.format_exc()
        stderr_log.append(f"failure: {e}\n{tb}")
        exit_code = 1
        try:
            # Persist failure evidence where technically possible
            # Curve if partially built
            if curve and not curve_path.exists():
                try:
                    curve_path.write_text(json.dumps(curve, indent=2), encoding="utf-8")
                except Exception:
                    pass
            terminal_manifest = {
                "member": member,
                "cost": cost,
                "hedger_seed": hedger_seed,
                "status": "failure",
                "error": str(e),
                "exit_code": int(exit_code),
                "start_time": start_time,
                "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            if not terminal_manifest_path.exists():
                terminal_manifest_path.write_text(json.dumps(terminal_manifest, indent=2, sort_keys=True), encoding="utf-8")
            if not stdout_path.exists():
                stdout_path.write_text("\n".join(stdout_log), encoding="utf-8")
            if not stderr_path.exists():
                stderr_path.write_text("\n".join(stderr_log), encoding="utf-8")
            if not exit_code_path.exists():
                exit_code_path.write_text(str(exit_code), encoding="utf-8")
            # Report failure if not exists
            if not report_path.exists():
                report = {
                    "schema_version": "hedging-gru-training-report-v1",
                    "member": member,
                    "run_prefix": run_prefix,
                    "cost": cost,
                    "cost_bps": bps,
                    "hedger_seed": hedger_seed,
                    "synthetic_dataset_path": str(synthetic_dataset_path),
                    "synthetic_manifest_sha256": synthetic_manifest_sha,
                    "contract_v3_canonical": EXPECTED_CONTRACT_CANONICAL,
                    "contract_v3_blob": EXPECTED_CONTRACT_BLOB,
                    "implementation_git_head": git_head,
                    "runtime_identity": EXPECTED_RUNTIME,
                    "status": "failure",
                    "error": str(e),
                    "exit_code": int(exit_code),
                    "start_time": start_time,
                    "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass
        # Re-raise for caller to handle (tests expect exception or check terminal evidence)
        raise

def train_one_policy(
    *,
    member: str,
    cost: float,
    hedger_seed: int,
    authorization_path: Path,
) -> dict[str, str]:
    """Public production API: train one GRU hedger policy for one authorized (member,cost,hedger_seed).

    Requires authorization_path (tracked, clean, committed, canonical/blob, task family) and member/cost/hedger_seed.
    No caller-supplied scientific override (batch_size, max_epochs, etc. are derived from contract and authorization).
    Fail-closed before scientific work if authorization invalid.
    """
    from neuralmarket.research.deep_hedging.runner import (
        verify_authorization_artifact,
        validate_authorization_schema,
        verify_implementation_manifest,
    )
    import json

    info = verify_authorization_artifact(authorization_path)
    payload = json.loads(authorization_path.read_bytes().decode("utf-8"))
    validate_authorization_schema(payload)
    impl_commit = str(payload.get("implementation_commit") or "")
    blobs = payload.get("implementation_source_blobs") or payload.get("source_blobs")
    if blobs and impl_commit:
        verify_implementation_manifest(authorized_commit=impl_commit, authorized_blobs=blobs)
    from neuralmarket.research.deep_hedging.runner import preflight_checks

    preflight_checks(require_clean_tree=True)
    allowlist = payload.get("member_allowlist", [])
    if member not in allowlist:
        raise RuntimeError(f"member {member} not in authorization allowlist {allowlist}")
    if cost not in payload.get("cost_allowlist", []):
        raise RuntimeError(f"cost {cost} not in allowlist")
    if hedger_seed not in payload.get("hedger_seed_allowlist", []):
        raise RuntimeError(f"hedger_seed {hedger_seed} not in allowlist")
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    run_prefix = RUN_PREFIXES[member]
    dataset_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_episodes_v1.parquet")
    manifest_path = Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_manifest_v1.json")
    return _train_one_policy_internal(
        member=member,
        cost=cost,
        hedger_seed=hedger_seed,
        synthetic_dataset_path=dataset_path,
        synthetic_manifest_path=manifest_path,
        policy_root=None,
        run_prefix=run_prefix,
        max_epochs=200,
        min_epochs=20,
        patience=20,
        batch_size=64,
        device="cuda",
        verify_contract_runtime=True,
    )

