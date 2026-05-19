"""Lightweight FX conversion for display-only balance currency switching."""

from __future__ import annotations

import json
import time
import urllib.request

from deepseek_balance_monitor_mac.config import log


_CACHE: dict[tuple[str, str], tuple[float, float]] = {}
_TTL_SECONDS = 60 * 30


def get_rate(from_currency: str, to_currency: str) -> float:
    from_currency = (from_currency or "").upper()
    to_currency = (to_currency or "").upper()
    if not from_currency or not to_currency:
        raise ValueError("Currency code is required")
    if from_currency == to_currency:
        return 1.0

    cache_key = (from_currency, to_currency)
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[1] < _TTL_SECONDS:
        return cached[0]

    url = f"https://api.frankfurter.dev/v2/rate/{from_currency}/{to_currency}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rate = float(data["rate"])
        _CACHE[cache_key] = (rate, now)
        return rate
    except Exception as e:
        log(f"Exchange rate lookup failed ({from_currency}->{to_currency}): {e}")
        raise
