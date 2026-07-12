import pytest

import neuralmarket


@pytest.mark.unit
def test_package_imports() -> None:
    assert neuralmarket is not None


@pytest.mark.unit
def test_package_version_available() -> None:
    assert isinstance(neuralmarket.__version__, str)
    assert neuralmarket.__version__


@pytest.mark.unit
def test_core_modules_import() -> None:
    from neuralmarket.core import (
        configuration,
        environment,
        logging,
        reproducibility,
    )

    assert configuration is not None
    assert environment is not None
    assert logging is not None
    assert reproducibility is not None
