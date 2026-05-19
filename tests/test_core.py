import tempfile
import urllib.error
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from deepseek_balance_monitor_mac import api_client
from deepseek_balance_monitor_mac.config import DEFAULT_CONFIG, T
from deepseek_balance_monitor_mac.app_state import AppState
from deepseek_balance_monitor_mac.core.monitoring import AlertTracker, format_fetch_error, get_display_balance, get_preferred_balance
from deepseek_balance_monitor_mac.storage import _sum_consumption_drops

# Skip macOS-specific tests on non-macOS platforms
if sys.platform == "darwin":
    from deepseek_balance_monitor_mac.mac.keystore import decrypt_api_key, encrypt_api_key
else:
    decrypt_api_key = encrypt_api_key = None

class ApiClientTests(unittest.TestCase):
    def test_fetch_balance_parses_currency_amounts(self):
        payload = {
            "is_available": False,
            "balance_infos": [{
                "currency": "CNY",
                "total_balance": "12.50", "granted_balance": "2.00",
                "topped_up_balance": "10.50",
            }],
        }
        with patch("deepseek_balance_monitor_mac.api_client._get_json", return_value=payload):
            result = api_client.fetch_balance("key")
        self.assertFalse(result["is_available"])
        balance = result["all_balances"]["CNY"]
        self.assertEqual((balance["total_balance"], balance["granted_balance"],
                          balance["topped_up_balance"]), (12.5, 2.0, 10.5))

    def test_fetch_balance_handles_empty_and_unauthorized_responses(self):
        with patch("deepseek_balance_monitor_mac.api_client._get_json", return_value={"balance_infos": []}):
            with self.assertRaises(ValueError):
                api_client.fetch_balance("key")
        error = urllib.error.HTTPError("url", 401, "", {}, None)
        with patch("deepseek_balance_monitor_mac.api_client._get_json", side_effect=error):
            with self.assertRaises(PermissionError):
                api_client.fetch_balance("bad-key")
        error.close()

    def test_fetch_service_status_reports_api_component_state(self):
        # Verify the function returns a dict with expected keys on success
        # (parsing details depend on FlashDuty RSC format, tested manually)
        html = '{\\"name\\":\\"API\\"}'
        mock_resp = Mock()
        mock_resp.read.return_value = html.encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = api_client.fetch_service_status()
        self.assertIn("indicator", result)
        self.assertIn("api_operational", result)
        self.assertIsInstance(result["api_operational"], bool)

        # Network error returns None
        with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
            self.assertIsNone(api_client.fetch_service_status())

class AppStateTests(unittest.TestCase):
    def _state(self, alert_mode="once", threshold=10):
        config = {"language": "en", "threshold_yuan": threshold,
                  "alert_mode": alert_mode}
        with patch("deepseek_balance_monitor_mac.app_state.load_config", return_value=config):
            return AppState()

    def test_low_balance_alert_once_and_api_status_transitions(self):
        state = self._state()
        state.balances = {"CNY": {"total_balance": 5}}
        self.assertTrue(state.is_low_balance())
        self.assertTrue(state.should_alert())
        self.assertFalse(state.should_alert())
        state.balances["CNY"]["total_balance"] = 11
        self.assertFalse(state.should_alert())
        state.balances["CNY"]["total_balance"] = 5
        self.assertTrue(state.should_alert())
        state.service_status = {"api_operational": False}
        self.assertEqual(state.check_api_status_alert(), "degraded")
        self.assertIsNone(state.check_api_status_alert())
        state.service_status = {"api_operational": True}
        self.assertEqual(state.check_api_status_alert(), "recovered")

class ConfigContractTests(unittest.TestCase):
    def test_v12_config_fields_and_notification_text_exist(self):
        for key in ("retention_days", "theme", "icon_colors", "icon_stroke",
                    "export_path", "http_proxy", "currency"):
            self.assertIn(key, DEFAULT_CONFIG)

        english_line = T("bal_line", "en", balance="12.34", code="CNY",
                         topped="10.00", granted="2.34")
        self.assertEqual(english_line, "12.34 CNY (Topped 10.00, Granted 2.34)")
        self.assertEqual(T("service_status", "en"), "API Status:")


class MonitoringHelpersTests(unittest.TestCase):
    def test_preferred_balance_and_alert_tracker(self):
        balances = {
            "USD": {"total_balance": 8, "topped_up_balance": 7, "granted_balance": 1},
            "CNY": {"total_balance": 5, "topped_up_balance": 4, "granted_balance": 1},
        }
        preferred = get_preferred_balance(balances, "CNY")
        self.assertEqual(preferred["currency"], "CNY")
        self.assertEqual(preferred["total_balance"], 5)

        tracker = AlertTracker()
        self.assertTrue(tracker.should_notify_low_balance(preferred, 10, "once"))
        self.assertFalse(tracker.should_notify_low_balance(preferred, 10, "once"))
        self.assertTrue(tracker.should_notify_consumption(12.0, 10.0, "once"))
        self.assertFalse(tracker.should_notify_consumption(12.0, 10.0, "once"))
        self.assertFalse(tracker.should_notify_consumption(8.0, 10.0, "once"))
        self.assertTrue(tracker.should_notify_consumption(12.0, 10.0, "once"))
        self.assertEqual(tracker.service_status_transition({"api_operational": False}), "degraded")
        self.assertIsNone(tracker.service_status_transition({"api_operational": False}))
        self.assertEqual(tracker.service_status_transition({"api_operational": True}), "recovered")

    def test_display_balance_converts_when_preferred_currency_missing(self):
        balances = {
            "CNY": {"total_balance": 10, "topped_up_balance": 8, "granted_balance": 2},
        }
        converted = get_display_balance(
            balances,
            "USD",
            rate_provider=lambda from_code, to_code: 0.15 if (from_code, to_code) == ("CNY", "USD") else 1.0,
        )
        self.assertEqual(converted["currency"], "USD")
        self.assertEqual(converted["source_currency"], "CNY")
        self.assertEqual(converted["total_balance"], 1.5)
        self.assertEqual(converted["topped_up_balance"], 1.2)
        self.assertEqual(converted["granted_balance"], 0.3)

    def test_format_fetch_error_maps_http_codes(self):
        err_503 = urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None)
        err_429 = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        self.assertIn("503", format_fetch_error(err_503))
        self.assertIn("429", format_fetch_error(err_429))
        self.assertEqual(format_fetch_error(PermissionError("Invalid API Key")), "Invalid API Key")
        err_503.close()
        err_429.close()

    def test_today_consumption_sum_ignores_topups(self):
        self.assertEqual(_sum_consumption_drops([11.21, 10.88]), 0.33)
        self.assertEqual(_sum_consumption_drops([10.0, 9.5, 12.0, 11.2, 10.8]), 1.7)
        self.assertEqual(_sum_consumption_drops([10.0, 12.0, 12.0]), 0.0)

@unittest.skipUnless(sys.platform == "darwin", "macOS only")
class MacKeystoreTests(unittest.TestCase):
    def test_mac_keystore_round_trip_and_wrong_key_returns_empty(self):
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as other:
            encrypted = encrypt_api_key("test-key-value", Path(data))

            self.assertEqual(decrypt_api_key(encrypted, Path(data)), "test-key-value")
            self.assertEqual(decrypt_api_key(encrypted, Path(other)), "")
