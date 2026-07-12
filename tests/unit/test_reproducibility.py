import random
import sys
import types

import numpy as np
import pytest

from neuralmarket.core.reproducibility import DEFAULT_SEED, seed_everything


def _fake_torch(cuda_available: bool) -> types.ModuleType:
    seen: dict[str, object] = {}
    module = types.ModuleType("torch")
    module.manual_seed = lambda s: seen.__setitem__("manual", s)  # type: ignore[attr-defined]
    module.use_deterministic_algorithms = (  # type: ignore[attr-defined]
        lambda *a, **k: seen.__setitem__("deterministic", True)
    )
    module.cuda = types.SimpleNamespace(  # type: ignore[attr-defined]
        is_available=lambda: cuda_available,
        manual_seed_all=lambda s: seen.__setitem__("cuda", s),
        device_count=lambda: 1 if cuda_available else 0,
    )
    module._seen = seen  # type: ignore[attr-defined]
    return module


@pytest.mark.unit
def test_default_seed_value() -> None:
    assert DEFAULT_SEED == 1337


@pytest.mark.unit
def test_python_random_reproducible() -> None:
    seed_everything(123)
    first = [random.random() for _ in range(5)]
    seed_everything(123)
    second = [random.random() for _ in range(5)]
    assert first == second


@pytest.mark.unit
def test_numpy_reproducible() -> None:
    seed_everything(123)
    first = np.random.rand(10)
    seed_everything(123)
    second = np.random.rand(10)
    assert np.array_equal(first, second)


@pytest.mark.unit
def test_different_seeds_differ() -> None:
    seed_everything(1)
    first = np.random.rand(10)
    seed_everything(2)
    second = np.random.rand(10)
    assert not np.array_equal(first, second)


@pytest.mark.unit
def test_negative_seed_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        seed_everything(-5)


@pytest.mark.unit
def test_seed_returns_applied_value() -> None:
    assert seed_everything(77) == 77


@pytest.mark.unit
def test_seeding_without_torch_ok() -> None:
    # PyTorch is not a dependency of this foundation; seeding must still succeed.
    assert seed_everything(DEFAULT_SEED) == DEFAULT_SEED


@pytest.mark.unit
def test_seed_with_fake_torch_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_torch(cuda_available=False)
    monkeypatch.setitem(sys.modules, "torch", fake)
    assert seed_everything(9, deterministic=True) == 9
    assert fake._seen["manual"] == 9  # type: ignore[attr-defined]
    assert "cuda" not in fake._seen  # type: ignore[attr-defined]
    assert fake._seen["deterministic"] is True  # type: ignore[attr-defined]


@pytest.mark.unit
def test_seed_with_fake_torch_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_torch(cuda_available=True)
    monkeypatch.setitem(sys.modules, "torch", fake)
    assert seed_everything(9, deterministic=True) == 9
    assert fake._seen["cuda"] == 9  # type: ignore[attr-defined]
