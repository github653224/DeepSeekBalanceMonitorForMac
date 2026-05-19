"""Monitoring helpers shared by macOS and legacy Python entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
import urllib.error


def get_preferred_balance(balances: dict, preferred_currency: str = "CNY"):
    """Return the preferred currency balance, or the first available balance."""
    if preferred_currency in balances:
        return {**balances[preferred_currency], "currency": preferred_currency}
    for code, balance in balances.items():
        return {**balance, "currency": code}
    return None


def convert_balance(balance: dict, from_currency: str, to_currency: str, rate: float):
    """Convert a balance dict into another currency using a single FX rate."""
    return {
        "currency": to_currency,
        "source_currency": from_currency,
        "exchange_rate": rate,
        "total_balance": round(balance["total_balance"] * rate, 2),
        "granted_balance": round(balance["granted_balance"] * rate, 2),
        "topped_up_balance": round(balance["topped_up_balance"] * rate, 2),
    }


def get_display_balance(
    balances: dict,
    preferred_currency: str = "CNY",
    rate_provider=None,
):
    """Return a display balance in the preferred currency when possible.

    If the preferred currency is missing from the API payload and a rate provider
    is available, the first balance is converted for display only.
    """
    preferred = get_preferred_balance(balances, preferred_currency)
    if preferred and preferred.get("currency") == preferred_currency:
        return preferred

    if not balances:
        return None

    source = get_preferred_balance(balances)
    if source is None:
        return None

    if source["currency"] == preferred_currency or rate_provider is None:
        return source

    try:
        rate = rate_provider(source["currency"], preferred_currency)
    except Exception:
        rate = None
    if not rate:
        return source
    return convert_balance(source, source["currency"], preferred_currency, rate)


def is_low_balance(balance: dict | None, threshold: float) -> bool:
    return bool(balance and balance["total_balance"] < threshold)


def format_fetch_error(error: Exception) -> str:
    """Map transport errors to short, user-facing messages."""
    if isinstance(error, PermissionError):
        return str(error)
    if isinstance(error, urllib.error.HTTPError):
        if error.code == 503:
            return "DeepSeek API temporarily unavailable (503 Service Unavailable)"
        if error.code == 429:
            return "DeepSeek API rate limit reached (429 Too Many Requests)"
        return f"DeepSeek API request failed ({error.code} {error.reason})"
    return str(error).split("\n")[0]


@dataclass
class AlertTracker:
    """Stateful helper for low-balance and API transition notifications."""

    low_balance_suppressed: bool = False
    consumption_suppressed: bool = False
    api_was_operational: bool = True

    def should_notify_low_balance(self, balance: dict | None, threshold: float, mode: str) -> bool:
        if mode == "never":
            self.low_balance_suppressed = False
            return False
        low = is_low_balance(balance, threshold)
        if not low:
            self.low_balance_suppressed = False
            return False
        if mode == "always":
            return True
        if self.low_balance_suppressed:
            return False
        self.low_balance_suppressed = True
        return True

    def should_notify_consumption(self, daily_rate: float | None, threshold: float, mode: str) -> bool:
        if threshold <= 0 or daily_rate is None:
            self.consumption_suppressed = False
            return False
        if mode == "never":
            self.consumption_suppressed = False
            return False
        high = daily_rate > threshold
        if not high:
            self.consumption_suppressed = False
            return False
        if mode == "always":
            return True
        if self.consumption_suppressed:
            return False
        self.consumption_suppressed = True
        return True

    def service_status_transition(self, service_status: dict | None):
        if service_status is None:
            return None
        now_ok = service_status.get("api_operational", True)
        was_ok = self.api_was_operational
        self.api_was_operational = now_ok
        if was_ok and not now_ok:
            return "degraded"
        if not was_ok and now_ok:
            return "recovered"
        return None
