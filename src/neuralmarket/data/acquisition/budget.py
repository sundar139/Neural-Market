"""Typed, ``Decimal``-based acquisition budget policy.

All money fields use :class:`decimal.Decimal` to avoid binary-float rounding
hazards. Internal arithmetic keeps full ``Decimal`` precision; only display
values are rounded, using round-half-up to the cent.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_CENT = Decimal("0.01")


def round_usd(value: Decimal) -> Decimal:
    """Round a USD amount to the cent using round-half-up, for display only."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def to_decimal(value: Any) -> Decimal:
    """Coerce a config/JSON value to ``Decimal``, rejecting binary floats.

    Args:
        value: A string, int, or ``Decimal`` amount.

    Returns:
        The value as a ``Decimal``.

    Raises:
        ValueError: If ``value`` is a ``float`` (binary-float amounts are
            rejected outright to avoid silent precision loss) or is otherwise
            not convertible to ``Decimal``.
    """
    if isinstance(value, float):
        raise ValueError("monetary amounts must be given as strings or Decimal, not float")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"not a valid decimal amount: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"not a finite decimal amount: {value!r}")
    return parsed


_MONEY_FIELDS = (
    "available_credit_usd",
    "maximum_project_spend_usd",
    "minimum_unspent_reserve_usd",
    "maximum_pilot_spend_usd",
    "maximum_single_future_request_usd",
    "maximum_development_quote_spend_usd",
    "minimum_final_test_quote_reserve_usd",
)


class BudgetPolicy(BaseModel):
    """Hard spending ceiling and reserve requirements for data acquisition.

    Required invariant:
    ``maximum_project_spend_usd + minimum_unspent_reserve_usd <= available_credit_usd``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    available_credit_usd: Decimal
    maximum_project_spend_usd: Decimal
    minimum_unspent_reserve_usd: Decimal
    maximum_pilot_spend_usd: Decimal
    maximum_single_future_request_usd: Decimal
    maximum_development_quote_spend_usd: Decimal
    minimum_final_test_quote_reserve_usd: Decimal
    require_manual_purchase_approval: bool
    purchase_authorized: bool

    @field_validator(*_MONEY_FIELDS, mode="before")
    @classmethod
    def _coerce_money(cls, value: Any) -> Decimal:
        return to_decimal(value)

    @model_validator(mode="after")
    def _check_invariants(self) -> BudgetPolicy:
        for name in _MONEY_FIELDS:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if (
            self.maximum_project_spend_usd + self.minimum_unspent_reserve_usd
            > self.available_credit_usd
        ):
            raise ValueError(
                "maximum_project_spend_usd + minimum_unspent_reserve_usd must not "
                "exceed available_credit_usd"
            )
        if self.maximum_pilot_spend_usd > self.maximum_project_spend_usd:
            raise ValueError("maximum_pilot_spend_usd must not exceed maximum_project_spend_usd")
        if self.maximum_single_future_request_usd > self.maximum_project_spend_usd:
            raise ValueError(
                "maximum_single_future_request_usd must not exceed maximum_project_spend_usd"
            )
        if (
            self.maximum_development_quote_spend_usd + self.minimum_final_test_quote_reserve_usd
            > self.maximum_project_spend_usd
        ):
            raise ValueError(
                "maximum_development_quote_spend_usd + "
                "minimum_final_test_quote_reserve_usd must not exceed "
                "maximum_project_spend_usd"
            )
        if self.purchase_authorized:
            # No purchase logic exists in this milestone; a policy that already
            # claims authorization cannot be planned against safely.
            raise ValueError("purchase_authorized must be false for this milestone")
        return self

    @property
    def unspent_after_project_spend(self) -> Decimal:
        """Return the credit that remains unspent if the full project cap is used."""
        return self.available_credit_usd - self.maximum_project_spend_usd
