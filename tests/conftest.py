"""Root test configuration.

On this Windows machine torch's bundled DLLs (c10.dll) fail to initialize
(WinError 1114) if pandas/pyarrow is imported first: pyarrow bundles its own
``msvcp140.dll`` which shadows the system runtime torch expects.  The fix is
to preload the SYSTEM ``msvcp140.dll`` and import torch before anything else,
so every subsequent DLL binds to the system runtime.
"""

from __future__ import annotations

import contextlib
import ctypes
import os

if os.name == "nt":
    with contextlib.suppress(OSError):  # pragma: no cover - runtime present on CI
        ctypes.WinDLL("msvcp140.dll")

import torch  # noqa: F401  (must load before pandas/pyarrow)
