"""Typer CLI exposing the ``neuralmarket`` console command."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from neuralmarket import __version__
from neuralmarket.core.configuration import ConfigurationError, load_config
from neuralmarket.core.environment import (
    EnvironmentValidationError,
    collect_snapshot,
    validate_python,
)
from neuralmarket.core.logging import configure_logging, get_logger

_logger = get_logger(__name__)

app = typer.Typer(
    name="neuralmarket",
    help="NeuralMarket research foundation utilities.",
    add_completion=False,
)
environment_app = typer.Typer(help="Environment provenance and validation commands.")
app.add_typer(environment_app, name="environment")

_DEFAULT_CONFIG = Path("configs/reproducibility/default.yaml")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", help="Show the package version and exit.", is_eager=True
    ),
) -> None:
    """NeuralMarket foundation command-line interface."""
    if version:
        typer.echo(__version__)
        raise typer.Exit(code=0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


@environment_app.command("check")
def environment_check(
    config: Path = typer.Option(
        _DEFAULT_CONFIG,
        "--config",
        help="Path to the reproducibility configuration YAML file.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional path to write the JSON environment report.",
    ),
) -> None:
    """Validate the local environment and optionally write a JSON report.

    Exits non-zero on a genuine validation failure, such as an unreadable or
    invalid configuration or a Python version mismatch.
    """
    try:
        loaded = load_config(config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc

    configure_logging(loaded.log_level)

    try:
        validate_python(loaded)
        snapshot = collect_snapshot(loaded, config)
    except EnvironmentValidationError as exc:
        _logger.error("Environment validation failed: %s", exc)
        raise typer.Exit(code=1) from exc

    if output is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            _logger.error("Failed to write report to %s: %s", output, exc)
            raise typer.Exit(code=1) from exc
        _logger.info("Environment report written to %s", output)

    typer.echo(json.dumps(snapshot, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
