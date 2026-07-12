from decimal import Decimal

import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.budget import BudgetPolicy, round_usd, to_decimal

_VALID = {
    "available_credit_usd": "125.00",
    "maximum_project_spend_usd": "95.00",
    "minimum_unspent_reserve_usd": "30.00",
    "maximum_pilot_spend_usd": "5.00",
    "maximum_single_future_request_usd": "10.00",
    "maximum_development_quote_spend_usd": "45.00",
    "minimum_final_test_quote_reserve_usd": "25.00",
    "require_manual_purchase_approval": True,
    "purchase_authorized": False,
}


def _policy(**overrides: object) -> BudgetPolicy:
    return BudgetPolicy(**{**_VALID, **overrides})


@pytest.mark.unit
def test_valid_policy_constructs() -> None:
    policy = _policy()
    assert policy.available_credit_usd == Decimal("125.00")
    assert policy.unspent_after_project_spend == Decimal("30.00")


@pytest.mark.unit
def test_exact_reserve_boundary_is_accepted() -> None:
    # 95 + 30 == 125 exactly: the invariant is <=, so this must pass.
    _policy(maximum_project_spend_usd="95.00", minimum_unspent_reserve_usd="30.00")


@pytest.mark.unit
def test_project_plus_reserve_exceeding_credit_rejected() -> None:
    with pytest.raises(ValidationError, match="must not exceed available_credit_usd"):
        _policy(minimum_unspent_reserve_usd="30.01")


@pytest.mark.unit
def test_pilot_cap_exceeding_project_cap_rejected() -> None:
    with pytest.raises(ValidationError, match="maximum_pilot_spend_usd"):
        _policy(maximum_pilot_spend_usd="200.00")


@pytest.mark.unit
def test_single_request_cap_exceeding_project_cap_rejected() -> None:
    with pytest.raises(ValidationError, match="maximum_single_future_request_usd"):
        _policy(maximum_single_future_request_usd="200.00")


@pytest.mark.unit
def test_development_plus_test_reserve_exceeding_project_cap_rejected() -> None:
    with pytest.raises(ValidationError, match="minimum_final_test_quote_reserve_usd"):
        _policy(minimum_final_test_quote_reserve_usd="60.00")


@pytest.mark.unit
def test_purchase_authorized_true_rejected() -> None:
    with pytest.raises(ValidationError, match="purchase_authorized"):
        _policy(purchase_authorized=True)


@pytest.mark.unit
@pytest.mark.parametrize("field", [k for k in _VALID if k.endswith("usd")])
def test_nonpositive_money_field_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        _policy(**{field: "0"})


@pytest.mark.unit
def test_float_amount_rejected() -> None:
    with pytest.raises(ValidationError):
        _policy(available_credit_usd=125.0)


@pytest.mark.unit
def test_to_decimal_rejects_float() -> None:
    with pytest.raises(ValueError, match="not.*float|float"):
        to_decimal(1.5)


@pytest.mark.unit
def test_to_decimal_accepts_str_int_decimal() -> None:
    assert to_decimal("1.50") == Decimal("1.50")
    assert to_decimal(5) == Decimal(5)
    assert to_decimal(Decimal("2.5")) == Decimal("2.5")


@pytest.mark.unit
def test_to_decimal_rejects_unparseable_string() -> None:
    with pytest.raises(ValueError):
        to_decimal("not-a-number")


@pytest.mark.unit
def test_round_usd_half_up() -> None:
    assert round_usd(Decimal("1.005")) == Decimal("1.01")
    assert round_usd(Decimal("1.004")) == Decimal("1.00")
    assert round_usd(Decimal("0")) == Decimal("0.00")
