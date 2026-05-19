"""Unified secret storage access across Python app variants."""

from __future__ import annotations

import sys

from deepseek_balance_monitor_mac.config import CONFIG_DIR


def read_api_key(config: dict | None = None) -> str:
    cfg = config or {}
    if sys.platform == "darwin":
        try:
            from deepseek_balance_monitor_mac.mac.keystore import decrypt_api_key

            encrypted = cfg.get("api_key_enc", "")
            if encrypted:
                value = decrypt_api_key(encrypted, CONFIG_DIR).strip()
                if value:
                    return value
        except Exception:
            pass

    try:
        from deepseek_balance_monitor_mac.secure_settings import read_api_key as read_secure_api_key

        value = read_secure_api_key()
        if value:
            return value.strip()
    except Exception:
        pass

    try:
        from deepseek_balance_monitor_mac.credential_store import read_credential

        value = read_credential()
        if value:
            return value.strip()
    except Exception:
        pass

    return cfg.get("api_key", "").strip()


def store_api_key(api_key: str, config: dict | None = None) -> dict:
    cfg = dict(config or {})
    api_key = api_key.strip()
    if sys.platform == "darwin":
        from deepseek_balance_monitor_mac.mac.keystore import encrypt_api_key

        encrypted = encrypt_api_key(api_key, CONFIG_DIR)
        if encrypted:
            cfg["api_key_enc"] = encrypted
            cfg.pop("api_key", None)
        else:
            cfg["api_key_enc"] = ""
            cfg["api_key"] = api_key
        return cfg

    stored = False
    try:
        from deepseek_balance_monitor_mac.secure_settings import store_api_key as store_secure_api_key

        store_secure_api_key(api_key)
        stored = True
    except Exception:
        pass

    if not stored:
        try:
            from deepseek_balance_monitor_mac.credential_store import store_credential

            store_credential(api_key)
            stored = True
        except Exception:
            pass

    if not stored:
        cfg["api_key"] = api_key
    return cfg
