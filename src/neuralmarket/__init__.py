"""NeuralMarket: reproducible research foundation for neural SDE market simulation.

This package currently provides reproducibility, configuration, and environment
diagnostics only. Data ingestion, models, and hedging policies are intentionally
deferred to later, separately validated implementation work.
"""

from __future__ import annotations

import os as _os

if _os.name == "nt":
    # Windows DLL-order fix: pyarrow bundles its own msvcp140.dll which, when
    # loaded first, makes torch's c10.dll fail to initialize (WinError 1114).
    # Preload the SYSTEM runtime so every later DLL binds to it.  Must run
    # before any pandas/pyarrow import, hence at package import time.
    import contextlib as _contextlib

    with _contextlib.suppress(OSError):  # pragma: no cover - runtime present on Windows
        import ctypes as _ctypes

        _ctypes.WinDLL("msvcp140.dll")

from importlib import metadata

try:
    __version__ = metadata.version("neuralmarket")
except metadata.PackageNotFoundError:  # pragma: no cover - only during source-tree use
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
