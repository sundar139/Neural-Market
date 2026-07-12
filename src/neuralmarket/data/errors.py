"""Domain-specific exceptions for market-data qualification and contracts.

Vendor-specific exceptions are translated into these domain errors inside the
source adapter so that provider details never leak into downstream code.
"""

from __future__ import annotations


class MarketDataError(Exception):
    """Base class for all market-data domain errors."""


class CredentialMissingError(MarketDataError):
    """Raised when a required provider credential is not configured."""


class AuthenticationError(MarketDataError):
    """Raised when the provider rejects the supplied credential."""


class EntitlementError(MarketDataError):
    """Raised when the account lacks entitlement for a dataset or schema."""


class DatasetUnavailableError(MarketDataError):
    """Raised when a requested dataset does not exist or is not accessible."""


class SchemaUnavailableError(MarketDataError):
    """Raised when a requested schema is not available for a dataset."""


class SymbolResolutionError(MarketDataError):
    """Raised when a symbol or parent symbology cannot be resolved."""


class PublisherError(MarketDataError):
    """Raised when a dataset's consolidated publisher cannot be identified."""


class CoverageError(MarketDataError):
    """Raised when available data does not cover the requested study window."""


class CostEstimationError(MarketDataError):
    """Raised when a cost estimate cannot be produced."""


class RateLimitError(MarketDataError):
    """Raised when the provider signals a rate limit."""


class ProviderNetworkError(MarketDataError):
    """Raised when a network failure prevents a provider request."""


class ManifestValidationError(MarketDataError):
    """Raised when a manifest fails schema or hash validation."""


class FinalTestAccessError(MarketDataError):
    """Raised on any attempt to access sealed final-test data."""


class ContractValidationError(MarketDataError):
    """Raised when a record violates a canonical contract invariant."""


class DownloadProhibitedError(MarketDataError):
    """Raised when qualification code attempts a prohibited data download."""


class AcquisitionNotAuthorizedError(MarketDataError):
    """Raised when acquisition-planning code attempts a download-capable operation.

    This milestone permits metadata-only acquisition planning; it never acquires,
    previews, or downloads market records.
    """


class BudgetPolicyError(MarketDataError):
    """Raised when a budget policy is internally inconsistent or unsafe."""


class PlanValidationError(MarketDataError):
    """Raised when an acquisition plan or policy manifest fails validation."""
