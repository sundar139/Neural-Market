"""Tiny dependency-free task/state helper for AI-assisted repository work."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

VALID_RISKS = {"R0", "R1", "R2", "R3", "R4", "R5"}
VALID_OUTCOMES = {
    "IMPLEMENTED",
    "VALIDATED",
    "BLOCKED",
    "NEEDS_DECISION",
    "NEEDS_EXTERNAL_ACTION",
    "SCIENTIFICALLY_INCONCLUSIVE",
}


def run_git(*args: str) -> str:
    """Run a read-only git command and return stripped stdout."""
    p = subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{p.stderr.strip()}")
    return p.stdout.strip()


def repo_root() -> Path:
    """Return the git repository root as a Path."""
    return Path(run_git("rev-parse", "--show-toplevel"))


def now() -> str:
    """Return the current local time as ISO-8601 with second precision."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def snapshot() -> dict:
    """Capture branch, HEAD, and working-tree status."""
    return {
        "branch": run_git("branch", "--show-current"),
        "head": run_git("rev-parse", "HEAD"),
        "tracked_status": run_git("status", "--short", "--untracked-files=no"),
        "full_status": run_git("status", "--short"),
        "captured_at": now(),
    }


def paths(root: Path) -> tuple[Path, Path, Path]:
    """Return and create the .agent-memory state, task, and evidence directories."""
    mem = root / ".agent-memory"
    tasks = mem / "tasks"
    evidence = mem / "evidence"
    mem.mkdir(exist_ok=True)
    tasks.mkdir(exist_ok=True)
    evidence.mkdir(exist_ok=True)
    return mem, tasks, evidence


def write_json(path: Path, value: dict) -> None:
    """Write a dict as pretty JSON at path."""
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path, default: dict | None = None) -> dict:
    """Read a JSON file, returning the default when it is missing."""
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_ignored(root: Path) -> None:
    """Append .agent-memory/ to .gitignore when absent."""
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    lines = text.splitlines()
    if ".agent-memory/" not in lines:
        sep = "" if not text or text.endswith("\n") else "\n"
        ignore.write_text(text + sep + ".agent-memory/\n", encoding="utf-8")


def cmd_init(_: argparse.Namespace) -> None:
    """Initialize .agent-memory state when absent."""
    root = repo_root()
    mem, _, _ = paths(root)
    ensure_ignored(root)
    state = mem / "state.json"
    if not state.exists():
        s = snapshot()
        write_json(
            state,
            {
                "project": root.name,
                "last_verified_commit": None,
                "current_task": None,
                "current_gate": "READY",
                "blockers": [],
                "next_action": None,
                "protected_invariants": [],
                "repository": s,
                "updated_at": now(),
            },
        )
    print(state)


def cmd_start(args: argparse.Namespace) -> None:
    """Open a task and record its start state."""
    if args.risk not in VALID_RISKS:
        raise SystemExit(f"risk must be one of: {', '.join(sorted(VALID_RISKS))}")

    root = repo_root()
    mem, tasks, evidence = paths(root)
    ensure_ignored(root)

    start = snapshot()
    if start["tracked_status"] and not args.allow_dirty:
        raise SystemExit(
            "Refusing to start: tracked working tree is dirty.\n"
            "Commit/stash/revert first, or deliberately pass --allow-dirty."
        )

    task = {
        "id": args.id,
        "objective": args.objective,
        "risk": args.risk,
        "started_at": now(),
        "start": start,
        "stop_conditions": args.stop_condition or [],
        "protected_invariants": args.invariant or [],
        "expected_files": args.expected_file or [],
        "outcome": None,
    }
    write_json(tasks / f"{args.id}.json", task)

    ev = evidence / f"{args.id}.md"
    if not ev.exists():
        ev.write_text(
            f"""# Evidence: {args.id}

## Objective

{args.objective}

## Risk

{args.risk}

## Discovery

## Decision

## Change

## Validation

## Invariants

## External effects

## Final state

## Residual risk

## Next action
""",
            encoding="utf-8",
        )

    state_path = mem / "state.json"
    state = load_json(state_path)
    state.update(
        {
            "project": root.name,
            "current_task": args.id,
            "current_gate": "DISCOVER",
            "blockers": [],
            "next_action": args.objective,
            "protected_invariants": args.invariant or [],
            "repository": start,
            "updated_at": now(),
        }
    )
    write_json(state_path, state)
    print(json.dumps({"task": task, "evidence": str(ev)}, indent=2))


def cmd_status(_: argparse.Namespace) -> None:
    """Print current task state merged with live repository state."""
    root = repo_root()
    mem, _, _ = paths(root)
    state = load_json(mem / "state.json")
    state["live_repository"] = snapshot()
    print(json.dumps(state, indent=2))


def cmd_gate(args: argparse.Namespace) -> None:
    """Advance the current task through a named gate."""
    root = repo_root()
    mem, _, _ = paths(root)
    state_path = mem / "state.json"
    state = load_json(state_path)
    state["current_gate"] = args.name.upper()
    state["updated_at"] = now()
    write_json(state_path, state)
    print(state["current_gate"])


def cmd_finish(args: argparse.Namespace) -> None:
    """Close the current task with an outcome and record final state."""
    if args.outcome not in VALID_OUTCOMES:
        raise SystemExit(f"outcome must be one of: {', '.join(sorted(VALID_OUTCOMES))}")

    root = repo_root()
    mem, tasks, _ = paths(root)
    state_path = mem / "state.json"
    state = load_json(state_path)

    task_id = args.id or state.get("current_task")
    if not task_id:
        raise SystemExit("No current task. Pass --id.")

    task_path = tasks / f"{task_id}.json"
    task = load_json(task_path)
    if not task:
        raise SystemExit(f"Unknown task: {task_id}")

    final = snapshot()
    task.update(
        {
            "outcome": args.outcome,
            "summary": args.summary,
            "finished_at": now(),
            "final": final,
        }
    )
    write_json(task_path, task)

    state.update(
        {
            "current_task": None,
            "current_gate": "READY"
            if args.outcome in {"IMPLEMENTED", "VALIDATED"}
            else args.outcome,
            "blockers": [] if args.outcome in {"IMPLEMENTED", "VALIDATED"} else [args.summary],
            "next_action": args.next_action,
            "repository": final,
            "last_verified_commit": (
                final["head"] if args.outcome == "VALIDATED" else state.get("last_verified_commit")
            ),
            "updated_at": now(),
        }
    )
    write_json(state_path, state)
    print(json.dumps(task, indent=2))


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse command parser."""
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("start")
    sp.add_argument("--id", required=True)
    sp.add_argument("--objective", required=True)
    sp.add_argument("--risk", required=True)
    sp.add_argument("--stop-condition", action="append")
    sp.add_argument("--invariant", action="append")
    sp.add_argument("--expected-file", action="append")
    sp.add_argument("--allow-dirty", action="store_true")
    sp.set_defaults(func=cmd_start)

    sp = sub.add_parser("status")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("gate")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_gate)

    sp = sub.add_parser("finish")
    sp.add_argument("--id")
    sp.add_argument("--outcome", required=True)
    sp.add_argument("--summary", required=True)
    sp.add_argument("--next-action")
    sp.set_defaults(func=cmd_finish)

    return p


def main() -> int:
    """Entry point; parse arguments and dispatch to the selected command."""
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
