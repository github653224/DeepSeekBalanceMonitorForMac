import os
import subprocess
import sys
import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import tempfile
import rumps

try:
    from AppKit import NSImage, NSColor, NSSize, NSBezierPath
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

# Colored SF Symbol config for API service status
_STATUS_SYMBOLS = {
    "none":        ("checkmark.circle", (0, 190, 0)),
    "minor":       ("exclamationmark.triangle.fill", (245, 185, 50)),
    "major":       ("xmark.circle.fill", (220, 70, 60)),
    "critical":    ("xmark.circle.fill", (220, 20, 30)),
    "maintenance": ("wrench.circle.fill", (245, 155, 50)),
    "_default":    ("questionmark.circle.fill", (140, 140, 150)),
    "_error":      ("exclamationmark.circle.fill", (185, 70, 60)),
}

from deepseek_balance_monitor_mac.config import load_config, save_config, T as _T, log, CONFIG_DIR
from deepseek_balance_monitor_mac.core.monitoring import AlertTracker, format_fetch_error, get_display_balance, get_preferred_balance, is_low_balance
from deepseek_balance_monitor_mac.infra.exchange_rates import get_rate
from deepseek_balance_monitor_mac.infra.secret_store import read_api_key
from deepseek_balance_monitor_mac.history_dialog import open_history

# WebView settings sentinel & PID
_SETTINGS_SENTINEL = CONFIG_DIR / ".settings_changed"
_SETTINGS_PID = CONFIG_DIR / "settings.pid"

# --- macOS Local Translations ---
_MAC_T = {
    "zh": {
        "topped_up": "充值余额",
        "granted": "赠送余额",
        "currency": "货币",
        "checking": "查询中…",
        "error_fetch": "查询出错",
        "check_now": "立即查询",
        "top_up": "充值",
        "settings": "设置",
        "quit": "退出",
    },
    "en": {
        "topped_up": "Topped Up",
        "granted": "Granted",
        "currency": "Currency",
        "checking": "Checking…",
        "error_fetch": "Fetch Error",
        "check_now": "Check Now",
        "top_up": "Top Up",
        "settings": "Settings",
        "quit": "Quit",
    }
}

def T(key, lang="zh", **kwargs):
    """Local translation wrapper that falls back to global T."""
    text = _MAC_T.get(lang, _MAC_T["zh"]).get(key)
    if text:
        return text.format(**kwargs) if kwargs else text
    return _T(key, lang, **kwargs)
from deepseek_balance_monitor_mac.api_client import fetch_balance, fetch_service_status
from deepseek_balance_monitor_mac.icon_renderer import _get_colors, _text_color
from deepseek_balance_monitor_mac.storage import get_consumption_rate, get_today_consumption, save_balance_record

# macOS system font attempts
import glob
_FONTS = []

# Helper to find font in bundle
def _get_bundle_path(rel_path):
    if getattr(sys, 'frozen', False):
        # PyInstaller _MEIPASS
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        # Inside .app bundle: Contents/Resources/rel_path
        alt_base = os.path.join(os.path.dirname(sys.executable), "..", "Resources")
        paths = [os.path.join(base, rel_path), os.path.join(alt_base, rel_path)]
        for p in paths:
            if os.path.exists(p): return p
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../", rel_path))

local_font = _get_bundle_path("assets/font/ShareTech-Regular.ttf")
if os.path.exists(local_font):
    _FONTS.append(local_font)
else:
    log(f"Warning: Bundled font not found at {local_font}")

# 2. Search user directories
_FONTS += glob.glob(os.path.expanduser("~/Library/Fonts/*Share*Tech*.ttf"))
_FONTS += glob.glob("/Library/Fonts/*Share*Tech*.ttf")

# 3. Fallback to system fonts
_FONTS += [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/SFNS.ttf"
]

_NOTIFICATION_APP = None
_APP_ICON_PATH = _get_bundle_path("assets/AppIcon.png")


def set_notification_target(app):
    global _NOTIFICATION_APP
    _NOTIFICATION_APP = app


def _open_notification_target():
    app = _NOTIFICATION_APP
    if app is None:
        return
    try:
        app.on_show_balance(None)
    except Exception as e:
        log(f"Notification target open failed: {e}")


def notify_mac(title, message, subtitle="", action="show_balance"):
    """Robust notification using AppKit with delegate (to force display) and osascript fallback."""
    success = False
    try:
        from Foundation import (
            NSUserNotification,
            NSUserNotificationCenter,
            NSObject,
            NSUserNotificationActivationTypeActionButtonClicked,
            NSUserNotificationActivationTypeContentsClicked,
        )
        from AppKit import NSImage
        
        # Define delegate to force notification display even if app is frontmost
        global _notif_delegate
        if '_notif_delegate' not in globals():
            class NotificationDelegate(NSObject):
                def userNotificationCenter_shouldPresentNotification_(self, center, notification):
                    return True
                def userNotificationCenter_didActivateNotification_(self, center, notification):
                    try:
                        activation_type = notification.activationType()
                    except Exception:
                        activation_type = None
                    try:
                        user_info = notification.userInfo() or {}
                        action_name = user_info.get("action")
                    except Exception:
                        action_name = None
                    if action_name in ("open_settings", "show_balance") and activation_type in (
                        NSUserNotificationActivationTypeContentsClicked,
                        NSUserNotificationActivationTypeActionButtonClicked,
                    ):
                        _open_notification_target()
                    try:
                        center.removeDeliveredNotification_(notification)
                    except Exception:
                        pass
            _notif_delegate = NotificationDelegate.alloc().init()

        notification = NSUserNotification.alloc().init()
        notification.setTitle_(title)
        if subtitle:
            notification.setSubtitle_(subtitle)
        notification.setInformativeText_(message)
        notification.setSoundName_("NSUserNotificationDefaultSoundName")
        notification.setIdentifier_(f"deepseek-balance-{int(time.time() * 1000)}")
        notification.setUserInfo_({"action": action})
        if action in ("open_settings", "show_balance"):
            notification.setHasActionButton_(True)
            notification.setActionButtonTitle_("显示")
        if os.path.exists(_APP_ICON_PATH):
            img = NSImage.alloc().initByReferencingFile_(_APP_ICON_PATH)
            if img:
                notification.setContentImage_(img)

        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        if center:
            center.setDelegate_(_notif_delegate)
            center.deliverNotification_(notification)
            success = True
            log("Native AppKit notification delivered")
    except Exception as e:
        log(f"Native notification failed: {e}")

    if not success:
        # Fallback to osascript
        try:
            import subprocess
            # osascript display notification doesn't like multiple lines well
            t = title.replace('"', '\\"')
            m = message.replace('\n', '  ').replace('"', '\\"')
            s = subtitle.replace('"', '\\"')
            script = f'display notification "{m}" with title "{t}"'
            if s: script += f' subtitle "{s}"'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            log("Osascript notification triggered")
        except Exception as e:
            log(f"Osascript notification failed: {e}")


def _is_live_settings_process(pid: int) -> bool:
    """Return True only when the settings subprocess is genuinely alive.

    macOS can leave unreaped child processes in a defunct (zombie) state.
    `os.kill(pid, 0)` still succeeds for those, so we also inspect the `ps`
    process state and treat zombies as not running.
    """
    try:
        proc = subprocess.run(
            ["ps", "-o", "state=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if proc.returncode != 0:
            return False
        state = proc.stdout.strip().upper()
        if not state or "Z" in state:
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def create_mac_icon(label: str, fill_color: tuple, text_color: tuple) -> str:
    """Render a macOS menubar icon with given colors.
    fill_color: RGBA tuple for background.
    text_color: RGBA tuple for label text.
    """
    scale = 4
    base_size = 18
    size = base_size * scale

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin_outer = 1.85 * scale
    radius = 2.75 * scale

    draw.rounded_rectangle([margin_outer, margin_outer, size - margin_outer, size - margin_outer],
                           radius=radius, fill=fill_color)

    font_size = 10 * scale
    font = None
    for fn in _FONTS:
        try:
            font = ImageFont.truetype(fn, font_size)
            font.path = fn
            break
        except Exception:
            continue
    if not font:
        font = ImageFont.load_default()

    margin_inner = 1 * scale
    while hasattr(font, 'getlength') and font.getlength(label) > (size - margin_outer*2 - margin_inner*2) and font_size > 6:
        font_size -= 0.5 * scale
        try:
            font = ImageFont.truetype(font.path, int(font_size))
            font.path = font.path
        except: break

    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), label, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (size - w) / 2 - bbox[0]
        y = (size - h) / 2 - bbox[1]
        draw.text((x, y), label, fill=text_color, font=font)
    else:
        draw.text((size/2, size/2), label, fill=text_color, font=font, anchor="mm")

    final_size = base_size * 2
    img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)

    icon_path = os.path.join(tempfile.gettempdir(), "ds_balance_mac_icon.png")
    img.save(icon_path)
    return icon_path


def create_status_dot(rgb, size=12, dot_size=7):
    """Create a small solid color dot for menu item status."""
    if not HAS_PYOBJC:
        return None
    try:
        img = NSImage.alloc().initWithSize_(NSSize(size, size))
        img.lockFocus()
        r, g, b = rgb
        color = NSColor.colorWithDeviceRed_green_blue_alpha_(r / 255.0, g / 255.0, b / 255.0, 1.0)
        color.setFill()
        x = (size - dot_size) / 2.0
        y = (size - dot_size) / 2.0
        path = NSBezierPath.bezierPathWithOvalInRect_(((x, y), (dot_size, dot_size)))
        path.fill()
        img.unlockFocus()
        img.setTemplate_(False)
        return img
    except Exception:
        return None

class DeepSeekBalanceMacApp(rumps.App):
    def __init__(self):
        super(DeepSeekBalanceMacApp, self).__init__("DS Balance", quit_button=None)
        set_notification_target(self)

        self.config = load_config()
        self.balances = {}
        self.last_check = None
        self.error = None
        self.service_status = None
        self._timer = None
        self._running = True
        self._dirty_ui = False
        self._dirty_menu = False
        self._history_open = False
        self._history_window = None
        self._tk_root = None
        self.demo_mode = False
        self._alerts = AlertTracker()
        self._settings_prompted = False
        self._status_dot_cache = {}

        # Watch for settings saved from the native settings window.
        threading.Thread(target=self._watch_settings_sentinel, daemon=True).start()

        # Build Menus
        self.info_item = rumps.MenuItem("...", callback=None)
        self.detail_topped = rumps.MenuItem("...", callback=self.on_show_balance)
        self.detail_granted = rumps.MenuItem("...", callback=self.on_show_balance)
        self.today_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.rate_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.last_check_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.api_status_item = rumps.MenuItem("...", callback=lambda _: None)

        self.rebuild_menus()
        self.update_ui()
        self.on_check_now(None)
        if not read_api_key(self.config):
            threading.Timer(0.4, lambda: self.on_settings(None)).start()

    @property
    def lang(self):
        return self.config.get("language", "zh")

    def rebuild_menus(self):
        self.menu.clear()
        
        self.info_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.detail_topped = rumps.MenuItem("...", callback=self.on_show_balance)
        self.detail_granted = rumps.MenuItem("...", callback=self.on_show_balance)
        self.today_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.last_check_item = rumps.MenuItem("...", callback=self.on_show_balance)
        self.api_status_item = rumps.MenuItem("...", callback=lambda _: None)

        self.menu.add(self.info_item)
        self.menu.add(self.detail_topped)
        self.menu.add(self.detail_granted)
        self.menu.add(self.today_item)
        self.menu.add(self.rate_item)
        self.menu.add(self.last_check_item)
        self.menu.add(rumps.separator)
        self.menu.add(self.api_status_item)
        self.menu.add(rumps.separator)

        str_check = T("check_now", self.lang)
        str_history = T("history", self.lang)
        str_topup = T("top_up", self.lang)
        str_set = T("settings", self.lang)
        str_quit = T("quit", self.lang)

        btn_check = rumps.MenuItem(str_check, callback=self.on_check_now)
        btn_history = rumps.MenuItem(str_history, callback=self.on_history)
        btn_topup = rumps.MenuItem(str_topup, callback=self.on_top_up)
        btn_set = rumps.MenuItem(str_set, callback=self.on_settings)
        btn_quit = rumps.MenuItem(str_quit, callback=self.on_quit)
        
        # Apply native SF Symbols if PyObjC is available
        if HAS_PYOBJC:
            from AppKit import NSSize
            def _add_sf(item, symbol_name):
                try:
                    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol_name, None)
                    if img:
                        new_img = NSImage.alloc().initWithSize_(NSSize(18, 18))
                        new_img.lockFocus()
                        orig_size = img.size()
                        scale = min(16.0 / orig_size.width, 16.0 / orig_size.height)
                        if scale > 1: scale = 1
                        new_w = orig_size.width * scale
                        new_h = orig_size.height * scale
                        x = (18 - new_w) / 2.0
                        y = (18 - new_h) / 2.0
                        img.drawInRect_(((x, y), (new_w, new_h)))
                        new_img.unlockFocus()
                        new_img.setTemplate_(True)
                        item._menuitem.setImage_(new_img)
                except Exception: pass
            
            _add_sf(btn_check, "arrow.triangle.2.circlepath")
            _add_sf(btn_history, "chart.line.uptrend.xyaxis")
            _add_sf(btn_topup, "creditcard")
            _add_sf(btn_set, "gearshape")
            _add_sf(btn_quit, "xmark.circle")

        self.menu.add(btn_check)
        self.menu.add(btn_history)
        self.menu.add(btn_topup)
        self.menu.add(btn_set)
        self.menu.add(rumps.separator)
        self.menu.add(btn_quit)

        self.update_ui()

    def get_preferred_balance(self):
        return get_display_balance(
            self.balances,
            self.config.get("currency", "CNY"),
            rate_provider=get_rate,
        )

    def _display_amount(self, amount: float | None, source_currency: str | None):
        if amount is None or source_currency is None:
            return None, None
        display_amount = round(float(amount), 2)
        display_currency = source_currency
        target_currency = self.config.get("currency", source_currency)
        if target_currency != source_currency:
            try:
                rate = get_rate(source_currency, target_currency)
                display_amount = round(display_amount * rate, 2)
                display_currency = target_currency
            except Exception:
                pass
        return display_amount, display_currency

    @rumps.timer(0.5)
    def update_ui_timer(self, _):
        # We need to update UI on the main thread. Rumps timers run on main thread.
        if getattr(self, '_dirty_ui', False):
            self.update_ui()
            self._dirty_ui = False
        if getattr(self, '_dirty_menu', False):
            try:
                self.rebuild_menus()
            except Exception as e:
                log(f"Menu rebuild error: {e}")
            self._dirty_menu = False

    def _set_sf_icon(self, item, symbol_name, rgb):
        """Apply a colored SF Symbol as a menu item image."""
        if not HAS_PYOBJC: return
        try:
            from AppKit import NSImage, NSColor, NSImageSymbolConfiguration
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol_name, None)
            if not img: return
            
            r, g, b = rgb
            color = NSColor.colorWithDeviceRed_green_blue_alpha_(r/255.0, g/255.0, b/255.0, 1.0)
            
            # Hierarchical coloring (macOS 12.0+)
            try:
                config = NSImageSymbolConfiguration.configurationWithHierarchicalColor_(color)
                colored_img = img.imageByApplyingSymbolConfiguration_(config)
                try:
                    colored_img.setTemplate_(False)
                except Exception:
                    pass
                item._menuitem.setImage_(colored_img)
            except:
                # Fallback to tinting (macOS 10.15+)
                try:
                    colored_img = img.imageWithTintColor_(color)
                    try:
                        colored_img.setTemplate_(False)
                    except Exception:
                        pass
                    item._menuitem.setImage_(colored_img)
                except:
                    item._menuitem.setImage_(img)
        except Exception as e:
            log(f"SF Symbol Error: {e}")

    def _set_status_dot(self, item, rgb):
        if not HAS_PYOBJC:
            return
        cached = self._status_dot_cache.get(rgb)
        if cached is None:
            cached = create_status_dot(rgb)
            self._status_dot_cache[rgb] = cached
        if cached is not None:
            item._menuitem.setImage_(cached)

    def trigger_ui_update(self):
        self._dirty_ui = True

    def update_ui(self):
        label = "..."
        is_error = self.error is not None
        missing_key = self.error == T("error_no_key", self.lang)

        # Determine theme-based colors
        colors = _get_colors(self.config)
        if missing_key:
            fill = colors["nodata"]
            label = "SET"
            self.info_item.title = T("setup_api_hint", self.lang)
            self.detail_topped.title = T("settings", self.lang)
            self.detail_granted.title = T("setup_api_subhint", self.lang)
            self.today_item.title = "..."
            self.rate_item.title = "..."
            self.last_check_item.title = "..."
            self.info_item.set_callback(self.on_settings)
            self.detail_topped.set_callback(self.on_settings)
            self.detail_granted.set_callback(self.on_settings)
            self.today_item.set_callback(None)
            self.rate_item.set_callback(None)
            self.last_check_item.set_callback(None)
        elif is_error:
            fill = colors["low"]
            label = "!"
            self.info_item.title = f"{T('error_fetch', self.lang)}: {self.error[:20]}"
            self.detail_topped.title = "..."
            self.detail_granted.title = "..."
            self.today_item.title = "..."
            self.rate_item.title = "..."
            self.last_check_item.title = "..."
            self.info_item.set_callback(self.on_show_balance)
            self.detail_topped.set_callback(None)
            self.detail_granted.set_callback(None)
            self.today_item.set_callback(None)
            self.rate_item.set_callback(None)
            self.last_check_item.set_callback(None)
        elif not self.balances:
            fill = colors["nodata"]
            label = "..."
            self.info_item.title = T("checking", self.lang)
            self.detail_topped.title = "..."
            self.detail_granted.title = "..."
            self.today_item.title = "..."
            self.rate_item.title = "..."
            self.last_check_item.title = "..."
            self.info_item.set_callback(None)
            self.detail_topped.set_callback(None)
            self.detail_granted.set_callback(None)
            self.today_item.set_callback(None)
            self.rate_item.set_callback(None)
            self.last_check_item.set_callback(None)
        else:
            b = self.get_preferred_balance()
            if b:
                val = int(b["total_balance"])
                t = float(self.config.get("threshold_yuan", 1.0))
                is_low = is_low_balance(b, t)
                fill = colors["low"] if is_low else colors["ok"]

                if val >= 10000:
                    label = f"{val//1000}k"
                elif val >= 1000:
                    label = f"{val/1000:.1f}k".replace(".0k", "k")
                else:
                    label = str(val)

                last_str = self.last_check.strftime("%Y-%m-%d %H:%M:%S") if self.last_check else "-"
                self.info_item.title = f"{T('total_balance', self.lang)}: {b['total_balance']:.2f} {b['currency']}"
                self.detail_topped.title = f"{T('topped_up', self.lang)}: {b['topped_up_balance']:.2f}"
                self.detail_granted.title = f"{T('granted', self.lang)}: {b['granted_balance']:.2f}"
                self.info_item.set_callback(self.on_show_balance)
                self.detail_topped.set_callback(self.on_show_balance)
                self.detail_granted.set_callback(self.on_show_balance)

                today = get_today_consumption()
                if today:
                    today_amount, source_currency = today
                    today_display, today_currency = self._display_amount(today_amount, source_currency)
                    if self.lang == "en":
                        self.today_item.title = f"{T('today_consumption', self.lang)}: {today_display:.2f} {today_currency}"
                    else:
                        self.today_item.title = f"{T('today_consumption', self.lang)}: {today_display:.2f} {today_currency}"
                    self.today_item.set_callback(self.on_show_today_usage)
                else:
                    self.today_item.title = f"{T('today_consumption', self.lang)}: --"
                    self.today_item.set_callback(None)

                cr = get_consumption_rate()
                if cr:
                    daily_rate, hours_left, source_currency = cr
                    daily_display, daily_currency = self._display_amount(daily_rate, source_currency)
                    days = int(hours_left // 24)
                    hrs = int(hours_left % 24)
                    if self.lang == "en":
                        self.rate_item.title = f"{T('avg_consumption', self.lang)}: {daily_display:.2f} {daily_currency}/day | Est: {days}d {hrs}h"
                    else:
                        self.rate_item.title = f"{T('avg_consumption', self.lang)}: {daily_display:.2f} {daily_currency}/天 | 预计可用: {days}天 {hrs}小时"
                    self.rate_item.set_callback(self.on_show_average_usage)
                else:
                    self.rate_item.title = T("not_enough_data", self.lang) if self.lang == "zh" else "Not enough data"
                    self.rate_item.set_callback(None)

                self.last_check_item.title = f"{T('last_check', self.lang)}: {last_str}"

        # API status line — use text symbols for consistent alignment in the menu.
        ss = self.service_status
        if ss:
            indicator = str(ss.get("indicator", "unknown")).lower()
            status_text = T(f"status_{indicator}", self.lang)
            prefix = {
                "none": "✅",
                "minor": "⚠️",
                "major": "❌",
                "critical": "❌",
                "maintenance": "🟠",
            }.get(indicator, "⚪")
            self.api_status_item.title = f"{prefix} {status_text}"
            if HAS_PYOBJC:
                self.api_status_item._menuitem.setImage_(None)
        elif missing_key:
            self.api_status_item.title = "..."
            if HAS_PYOBJC:
                self.api_status_item._menuitem.setImage_(None)
        elif is_error:
            self.api_status_item.title = f"⚪ {T('status_unknown', self.lang)}"
            if HAS_PYOBJC:
                self.api_status_item._menuitem.setImage_(None)
        else:
            self.api_status_item.title = "..."
            if HAS_PYOBJC:
                self.api_status_item._menuitem.setImage_(None)

        self.template = False
        text_c = _text_color(fill)
        self.icon = create_mac_icon(label, fill, text_c)

    def on_check_now(self, _):
        if self._timer:
            self._timer.cancel()
        self.trigger_ui_update()
        threading.Thread(target=self._do_check, daemon=True).start()

    def on_show_balance(self, _):
        if not self.balances:
            notify_mac(title=T("bal_empty_title", self.lang), message=T("bal_empty_msg", self.lang))
            return

        pb = self.get_preferred_balance()
        title = f"余额详情: {pb['total_balance']:.2f} {pb['currency']}" if pb else "余额详情"

        lines = []
        if pb:
            lines.append(
                f"{pb['currency']}: {pb['total_balance']:.2f} "
                f"(充值: {pb['topped_up_balance']:.2f}, 赠送: {pb['granted_balance']:.2f})"
            )
            source_currency = pb.get("source_currency")
            if source_currency and source_currency != pb["currency"]:
                lines.append(f"原始余额来源: {source_currency}  | 汇率: {pb.get('exchange_rate', 0):.5f}")

        for code, b in self.balances.items():
            if pb and code == pb["currency"]:
                continue
            lines.append(f"{code}: {b['total_balance']:.2f} (充值: {b['topped_up_balance']:.2f}, 赠送: {b['granted_balance']:.2f})")

        msg = "\n".join(lines)
        notify_mac(title=title, message=msg)

    def on_show_today_usage(self, _):
        today = get_today_consumption()
        if not today:
            notify_mac(
                title=T("today_consumption", self.lang),
                message=T("not_enough_data", self.lang),
                action="",
            )
            return

        today_amount, today_currency = self._display_amount(*today)
        if self.lang == "en":
            title = "Today's usage"
            message = f"Today: {today_amount:.2f} {today_currency}"
        else:
            title = "今日消耗"
            message = f"今日消耗: {today_amount:.2f} {today_currency}"
        notify_mac(title=title, message=message, action="")

    def on_show_average_usage(self, _):
        today = get_today_consumption()
        avg = get_consumption_rate()
        if not avg:
            notify_mac(
                title=T("avg_consumption", self.lang),
                message=T("not_enough_data", self.lang),
                action="",
            )
            return

        lines = []
        daily_rate, hours_left, source_currency = avg
        daily_display, daily_currency = self._display_amount(daily_rate, source_currency)
        days = int(hours_left // 24)
        hrs = int(hours_left % 24)
        if self.lang == "en":
            lines.append(f"Avg/day: {daily_display:.2f} {daily_currency}")
            lines.append(f"Est. remaining: {days}d {hrs}h")
            lines.append("Estimated from recent history.")
            title = "Average usage"
        else:
            lines.append(f"日均消耗: {daily_display:.2f} {daily_currency}/天")
            lines.append(f"预计可用: {days}天 {hrs}小时")
            lines.append("基于最近历史记录估算。")
            title = "日均消耗"

        notify_mac(title=title, message="\n".join(lines), action="")

    def on_top_up(self, _):
        import subprocess
        subprocess.run(["open", "https://platform.deepseek.com/top_up"])

    def on_history(self, _):
        try:
            if getattr(sys, "frozen", False):
                args = [sys.executable, "--history-native"]
            else:
                args = [sys.executable, "-m", "src.history_dialog"]
            subprocess.Popen(args, start_new_session=True)
            log("Native history launched as subprocess")
        except Exception as e:
            log(f"Failed to launch native history: {e}")
            try:
                open_history(self)
            except Exception as inner:
                log(f"Fallback inline history failed: {inner}")

    def _notify_api_transition(self, transition: str):
        if transition == "degraded":
            notify_mac(
                title=T("api_degraded_title", self.lang),
                message=T("api_degraded_msg", self.lang),
            )
        else:
            notify_mac(
                title=T("api_recovered_title", self.lang),
                message=T("api_recovered_msg", self.lang),
            )

    def _do_check(self):
        api_key = read_api_key(self.config)
        if not api_key:
            self.error = T("error_no_key", self.lang)
            self.balances = {}
            if not self._settings_prompted:
                self._settings_prompted = True
                self.on_settings(None)
        else:
            try:
                try:
                    self.service_status = fetch_service_status()
                except Exception:
                    self.service_status = None

                data = fetch_balance(api_key)
                self.balances = data["all_balances"]
                self.error = None
                self.last_check = datetime.now()
                log("Mac balance check OK")
                
                ss = self.service_status
                s_indicator = ss.get("indicator") if ss else None
                for code, bal in data["all_balances"].items():
                    save_balance_record(code, bal["total_balance"],
                                        bal["topped_up_balance"],
                                        bal["granted_balance"],
                                        service_status=s_indicator)
                log(f"Mac balance saved to DB ({len(data['all_balances'])} records)")
                
                b = self.get_preferred_balance()
                threshold = float(self.config.get("threshold_yuan", 1.0))
                consumption_threshold = float(self.config.get("consumption_alert_threshold", 0.0))
                mode = self.config.get("alert_mode", "once")
                if self._alerts.should_notify_low_balance(b, threshold, mode):
                    notify_mac(
                        title=T("low_bal_title", self.lang),
                        message=T(
                            "low_bal_msg",
                            self.lang,
                            balance=f"{b['total_balance']:.2f} {b['currency']}",
                            threshold=f"{threshold:.2f} {b['currency']}",
                        ),
                    )
                today_consumption = get_today_consumption()
                if today_consumption:
                    amount, source_currency = today_consumption
                    display_amount, display_currency = self._display_amount(amount, source_currency)
                    if self._alerts.should_notify_consumption(display_amount, consumption_threshold, mode):
                        notify_mac(
                            title=T("consumption_alert_title", self.lang),
                            message=T(
                                "consumption_alert_msg",
                                self.lang,
                                rate=f"{display_amount:.2f}",
                                code=display_currency,
                                threshold=f"{consumption_threshold:.2f}",
                            ),
                        )
                if self.config.get("api_alert_enabled", True):
                    transition = self._alerts.service_status_transition(self.service_status)
                    if transition:
                        self._notify_api_transition(transition)
            except Exception as e:
                self.error = format_fetch_error(e)
                self.balances = {}
                log(f"Mac check failed: {e}")
                
        self.trigger_ui_update()
        
        interval_min = int(self.config.get("interval_minutes", 10))
        self._timer = threading.Timer(interval_min * 60, self.on_check_now, args=(None,))
        self._timer.daemon = True
        self._timer.start()

    def _open_native_settings(self):
        """Launch the native Tk settings window as a subprocess."""
        if _SETTINGS_PID.exists():
            try:
                pid = int(_SETTINGS_PID.read_text().strip())
                if _is_live_settings_process(pid):
                    log(f"Native settings already running (pid {pid})")
                    if HAS_PYOBJC:
                        from AppKit import NSRunningApplication
                        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                        if app:
                            app.activateWithOptions_(3)
                    else:
                        subprocess.run(
                            ["osascript", "-e",
                             'tell app "System Events" to set frontmost of '
                             '(first process whose unix id is ' + str(pid) + ') to true'],
                            capture_output=True, timeout=5)
                    return True
                log(f"Removing stale settings pid {pid}")
                _SETTINGS_PID.unlink(missing_ok=True)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                _SETTINGS_PID.unlink(missing_ok=True)

        try:
            me = sys.executable
            if getattr(sys, "frozen", False):
                args = [me, "--settings-native"]
            else:
                args = [me, "-m", "src.mac.settings"]
            subprocess.Popen(args, start_new_session=True)
            log("Native settings launched as subprocess")
            return True
        except Exception as e:
            log(f"Failed to launch native settings: {e}")
            return False

    def _watch_settings_sentinel(self):
        """Background thread: reload config after the settings window saves."""
        while self._running:
            if _SETTINGS_SENTINEL.exists():
                try:
                    _SETTINGS_SENTINEL.unlink()
                    self.config = load_config()
                    self._dirty_menu = True
                    self._settings_prompted = False
                    self.on_check_now(None)
                    log("Settings changed via native window — config reloaded")
                except Exception as e:
                    log(f"Sentinel handler error: {e}")
            time.sleep(1)

    def on_settings(self, _):
        self._open_native_settings()
    
    def on_test_notify(self, _):
        notify_mac(
            title=T("low_bal_title", self.lang),
            subtitle="这是一条测试通知",
            message="在余额低于设定的阈值时，程序会自动弹出类似的警告提醒您充值。"
        )

    def on_quit(self, _):
        self._running = False
        if self._timer:
            self._timer.cancel()
        rumps.quit_application()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--settings-native":
        from deepseek_balance_monitor_mac.mac.settings import run_settings

        run_settings()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--show-balance":
        cfg = load_config()
        api_key = read_api_key(cfg)
        if not api_key:
            notify_mac(title=T("bal_empty_title", cfg.get("language", "zh")), message=T("error_no_key", cfg.get("language", "zh")))
            return
        try:
            data = fetch_balance(api_key)
            balances = data.get("all_balances", {})
            preferred = get_display_balance(
                balances,
                cfg.get("currency", "CNY"),
                rate_provider=get_rate,
            )
            if preferred:
                title = f"余额详情: {preferred['total_balance']:.2f} {preferred['currency']}"
                message = (
                    f"充值余额: {preferred['topped_up_balance']:.2f}\n"
                    f"赠送余额: {preferred['granted_balance']:.2f}"
                )
            else:
                title = T("bal_empty_title", cfg.get("language", "zh"))
                message = T("bal_empty_msg", cfg.get("language", "zh"))
            notify_mac(title=title, message=message, action="")
        except Exception as e:
            notify_mac(
                title=T("bal_empty_title", cfg.get("language", "zh")),
                message=format_fetch_error(e),
                action="",
            )
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--history-native":
        from deepseek_balance_monitor_mac.history_dialog import open_history

        class _HistoryAppStub:
            lang = load_config().get("language", "zh")
            config = load_config()
            demo_mode = False
            _history_open = False
            _history_window = None
            _tk_root = None

        open_history(_HistoryAppStub())
        return

    log("DeepSeek Balance Monitor (Mac version) starting")
    app = DeepSeekBalanceMacApp()
    app.run()


if __name__ == "__main__":
    main()
