"""NeuralMarket: reproducible research foundation for neural SDE market simulation.

This package currently provides reproducibility, configuration, and environment
diagnostics only. Data ingestion, models, and hedging policies are intentionally
deferred to later, separately validated implementation work.
"""

from importlib import metadata

try:
    __version__ = metadata.version("neuralmarket")
except metadata.PackageNotFoundError:  # pragma: no cover - only during source-tree use
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
