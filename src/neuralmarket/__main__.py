"""Module entry point so ``python -m neuralmarket`` mirrors the console script."""

from neuralmarket.cli.main import app


def main() -> None:
    """Invoke the Typer CLI application."""
    app()


if __name__ == "__main__":
    main()
