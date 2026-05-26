from __future__ import annotations

import importlib
import sys
import warnings
from threading import Thread
from typing import Any, cast

from app.menubar_runtime import (
    MenuBarRuntimeOptions,
    MenuBarRuntimeStatus,
    dashboard_page_url,
    start_menu_bar_runtime,
    status_from_options,
    stop_menu_bar_runtime,
    stopped_runtime_snapshot,
    sync_codex_provider,
)
from app.menubar_summary import (
    AccountMenuCard,
    MenuBarConfig,
    MenuBarDonutSummary,
    MenuBarSnapshot,
    fetch_menu_bar_snapshot,
)


def run_menu_bar_app(config: MenuBarConfig, *, runtime_options: MenuBarRuntimeOptions | None = None) -> None:
    if sys.platform != "darwin":
        raise SystemExit("The macOS menu bar app is only supported on macOS.")

    try:
        _run_cocoa_app(config, runtime_options)
    except ImportError as exc:
        raise SystemExit(
            "The macOS menu bar app requires PyObjC. Install dependencies with `uv sync` and try again."
        ) from exc


def _run_cocoa_app(config: MenuBarConfig, runtime_options: MenuBarRuntimeOptions | None) -> None:
    appkit = importlib.import_module("AppKit")
    foundation = importlib.import_module("Foundation")
    objc = importlib.import_module("objc")
    app_helper = importlib.import_module("PyObjCTools.AppHelper")
    warnings.filterwarnings("ignore", category=cast(type[Warning], getattr(objc, "ObjCPointerWarning")))

    NSApplication = getattr(appkit, "NSApplication")
    NSApplicationActivationPolicyAccessory = getattr(appkit, "NSApplicationActivationPolicyAccessory")
    NSBezierPath = getattr(appkit, "NSBezierPath")
    NSButton = getattr(appkit, "NSButton")
    NSColor = getattr(appkit, "NSColor")
    NSFont = getattr(appkit, "NSFont")
    NSMenu = getattr(appkit, "NSMenu")
    NSMenuItem = getattr(appkit, "NSMenuItem")
    NSRoundLineCapStyle = getattr(appkit, "NSRoundLineCapStyle", 1)
    NSStatusBar = getattr(appkit, "NSStatusBar")
    NSTextField = getattr(appkit, "NSTextField")
    NSView = getattr(appkit, "NSView")
    NSVariableStatusItemLength = getattr(appkit, "NSVariableStatusItemLength")
    NSWorkspace = getattr(appkit, "NSWorkspace")
    NSMakePoint = getattr(foundation, "NSMakePoint")
    NSMakeRect = getattr(foundation, "NSMakeRect")
    NSURL = getattr(foundation, "NSURL")
    NSObject = getattr(foundation, "NSObject")
    NSTimer = getattr(foundation, "NSTimer")
    call_after = getattr(app_helper, "callAfter")
    run_event_loop = getattr(app_helper, "runEventLoop")
    objc_super = getattr(objc, "super")

    def add_action(controller: Any, title: str, action: str) -> None:
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
        item.setTarget_(controller)
        controller.menu.addItem_(item)

    content_width = 360.0

    def add_view_item(menu: Any, view: Any) -> None:
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", None, "")
        item.setView_(view)
        menu.addItem_(item)

    def make_account_card_view(controller: Any, card: AccountMenuCard, index: int) -> Any:
        width = content_width
        height = 158.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(10)
        view.layer().setBorderWidth_(1)
        view.layer().setBorderColor_(card_border_color().CGColor())
        view.layer().setBackgroundColor_(card_background_color().CGColor())

        title = make_label(card.title, 14, True)
        title.setTextColor_(card_primary_text_color())
        title.setFrame_(NSMakeRect(14, 124, 190, 20))
        view.addSubview_(title)

        subtitle = make_label(card.subtitle, 12, False)
        subtitle.setTextColor_(card_secondary_text_color())
        subtitle.setFrame_(NSMakeRect(14, 104, 150, 18))
        view.addSubview_(subtitle)

        status = make_status_badge(card.status_label)
        status.setFrame_(NSMakeRect(width - 106, 122, 90, 24))
        view.addSubview_(status)

        if card.is_current:
            current = make_label("Current", 10, True)
            current.setTextColor_(NSColor.systemBlueColor())
            current.setFrame_(NSMakeRect(width - 86, 101, 70, 16))
            view.addSubview_(current)

        if card.shows_quota:
            add_usage_bar(view, "5h", card.primary_percent, card.primary_reset, 14, 52)
            add_usage_bar(view, "Weekly", card.secondary_percent, card.secondary_reset, 170, 52)
        else:
            platform_note = make_label("Platform fallback for compatible API routes", 11, False)
            platform_note.setTextColor_(card_secondary_text_color())
            platform_note.setFrame_(NSMakeRect(14, 69, width - 28, 16))
            view.addSubview_(platform_note)

        separator = NSView.alloc().initWithFrame_(NSMakeRect(14, 39, width - 28, 1))
        separator.setWantsLayer_(True)
        separator.layer().setBackgroundColor_(card_separator_color().CGColor())
        view.addSubview_(separator)

        details = NSButton.buttonWithTitle_target_action_("Details", controller, "openAccountDetails:")
        details.setBordered_(False)
        style_card_button(details)
        details.setTag_(index)
        details.setFrame_(NSMakeRect(9, 9, 74, 22))
        view.addSubview_(details)
        return view

    def make_quota_bars_header_view(controller: Any, *, can_show_donut: bool) -> Any:
        width = content_width
        height = 58.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        heading = make_label("Progress Bars", 16, True)
        heading.setFrame_(NSMakeRect(14, 28, 118, 22))
        view.addSubview_(heading)

        if can_show_donut:
            add_toggle_button(view, controller, "Show Donut", width - 216, 28, button_width=96)
        add_refresh_button(view, controller, width - 112, 28)
        return view

    def make_overview_view(
        rows: tuple[tuple[str, str], ...],
        donut: MenuBarDonutSummary | None,
        controller: Any | None = None,
    ) -> Any:
        if donut is not None:
            return make_primary_donut_view(donut, controller)

        row_map = dict(rows)
        width = content_width
        height = 126.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        heading = make_label("Overview", 11, True)
        heading.setTextColor_(NSColor.secondaryLabelColor())
        heading.setFrame_(NSMakeRect(14, 102, width - 28, 16))
        view.addSubview_(heading)

        left_items = (
            ("5h", row_map.get("5h remaining", "--")),
            ("7d", row_map.get("7d remaining", "--")),
            ("Requests", row_map.get("Requests", "--")),
            ("Tokens", row_map.get("Tokens", "--")),
        )
        right_items = (
            ("Cost", row_map.get("Cost", "--")),
            ("Error", row_map.get("Error rate", "--")),
            ("Accounts", row_map.get("Active accounts", "--")),
            ("Current", row_map.get("Current", "--")),
        )
        add_info_column(view, left_items, 14, 76)
        add_info_column(view, right_items, 176, 76)

        routing = make_label(f"Routing: {row_map.get('Routing', '--')}", 11, False)
        routing.setTextColor_(NSColor.secondaryLabelColor())
        routing.setFrame_(NSMakeRect(14, 6, width - 28, 14))
        view.addSubview_(routing)
        return view

    def make_primary_donut_view(donut: MenuBarDonutSummary, controller: Any | None) -> Any:
        width = content_width
        height = 196.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        heading = make_label(donut.title, 16, True)
        heading.setFrame_(NSMakeRect(14, 166, 180, 22))
        view.addSubview_(heading)

        if controller is not None:
            add_toggle_button(view, controller, "Show Progress Bars", width - 142, 166)
            add_refresh_button(view, controller, width - 112, 144)

        colors = donut_segment_colors()
        ring = OverviewDonutRingView.alloc().initWithDonut_colors_(donut, colors)
        ring.setFrame_(NSMakeRect(16, 42, 112, 112))
        view.addSubview_(ring)

        center_label = make_label(donut.center_label, 10, True)
        center_label.setAlignment_(2)
        center_label.setTextColor_(NSColor.secondaryLabelColor())
        center_label.setFrame_(NSMakeRect(35, 94, 74, 16))
        view.addSubview_(center_label)

        center_value = make_label(donut.center_value, 16, True)
        center_value.setAlignment_(2)
        center_value.setFrame_(NSMakeRect(35, 72, 74, 22))
        view.addSubview_(center_value)

        caption = make_label(donut.total_label, 12, False)
        caption.setTextColor_(NSColor.secondaryLabelColor())
        caption.setFrame_(NSMakeRect(20, 18, 126, 18))
        view.addSubview_(caption)

        legend_x = 148.0
        value_x = width - 64.0
        row_y = 124.0
        row_step = 20.0
        for index, segment in enumerate(donut.segments):
            add_donut_legend_row(
                view,
                color=colors[index % len(colors)],
                label=segment.label,
                value=format_menu_number(segment.value),
                x=legend_x,
                value_x=value_x,
                y=row_y - (index * row_step),
            )

        add_donut_legend_row(
            view,
            color=NSColor.systemGrayColor().colorWithAlphaComponent_(0.35),
            label=donut.used_label,
            value=format_menu_number(donut.used_value),
            x=legend_x,
            value_x=value_x,
            y=row_y - (len(donut.segments) * row_step),
        )
        return view

    def make_runtime_view(status: MenuBarRuntimeStatus, error: str) -> Any:
        width = content_width
        height = 80.0 if error else 64.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        heading = make_label("Server", 11, True)
        heading.setTextColor_(NSColor.secondaryLabelColor())
        heading.setFrame_(NSMakeRect(14, height - 24, width - 28, 16))
        view.addSubview_(heading)

        status_text = "Running" if status.running else "Stopped"
        if status.stale_metadata_removed:
            status_text = "Stopped (stale PID removed)"
        pid_text = "--" if status.pid is None else str(status.pid)
        add_info_column(
            view,
            (
                ("Status", status_text),
                ("PID", pid_text),
                ("Port", str(status.port)),
            ),
            14,
            height - 44,
        )
        log = make_label(str(status.log_file), 10, False)
        log.setTextColor_(NSColor.secondaryLabelColor())
        log.setFrame_(NSMakeRect(176, height - 44, 150, 14))
        view.addSubview_(log)
        if error:
            error_label = make_label(error, 10, False)
            error_label.setTextColor_(NSColor.systemRedColor())
            error_label.setFrame_(NSMakeRect(14, 8, width - 28, 14))
            view.addSubview_(error_label)
        return view

    def make_provider_sync_view(status: str, error: str) -> Any:
        width = content_width
        height = 52.0 if error else 36.0
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        heading = make_label("Provider Sync", 11, True)
        heading.setTextColor_(NSColor.secondaryLabelColor())
        heading.setFrame_(NSMakeRect(14, height - 24, 90, 16))
        view.addSubview_(heading)

        status_label = make_label(status, 11, False)
        status_label.setTextColor_(NSColor.labelColor())
        status_label.setFrame_(NSMakeRect(112, height - 24, width - 126, 16))
        view.addSubview_(status_label)

        if error:
            error_label = make_label(error, 10, False)
            error_label.setTextColor_(NSColor.systemRedColor())
            error_label.setFrame_(NSMakeRect(14, 8, width - 28, 14))
            view.addSubview_(error_label)
        return view

    def add_info_column(view: Any, items: tuple[tuple[str, str], ...], x: float, y: float) -> None:
        for index, (label, value) in enumerate(items):
            row_y = y - (index * 17)
            label_view = make_label(label, 11, False)
            label_view.setTextColor_(NSColor.secondaryLabelColor())
            label_view.setFrame_(NSMakeRect(x, row_y, 64, 14))
            view.addSubview_(label_view)

            value_view = make_label(value, 11, True)
            value_view.setTextColor_(NSColor.labelColor())
            value_view.setFrame_(NSMakeRect(x + 65, row_y, 78, 14))
            view.addSubview_(value_view)

    class OverviewDonutRingView(NSView):
        def initWithDonut_colors_(self, donut: MenuBarDonutSummary, colors: tuple[Any, ...]) -> Any:
            self = objc_super(OverviewDonutRingView, self).initWithFrame_(NSMakeRect(0, 0, 112, 112))
            if self is None:
                return None
            self.donut = donut
            self.colors = colors
            return self

        def isOpaque(self) -> bool:
            return False

        def drawRect_(self, _rect: Any) -> None:
            center = NSMakePoint(56.0, 56.0)
            radius = 44.0
            line_width = 16.0
            donut = self.donut
            total = max(float(donut.total_value), 1.0)

            track = NSBezierPath.bezierPath()
            track.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                center,
                radius,
                0.0,
                360.0,
                False,
            )
            track.setLineWidth_(line_width)
            NSColor.systemGrayColor().colorWithAlphaComponent_(0.25).setStroke()
            track.stroke()

            start_angle = 90.0
            for index, segment in enumerate(donut.segments):
                span = 360.0 * (max(0.0, float(segment.value)) / total)
                if span <= 0:
                    continue
                end_angle = start_angle - span
                arc = NSBezierPath.bezierPath()
                arc.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                    center,
                    radius,
                    start_angle,
                    end_angle,
                    True,
                )
                arc.setLineWidth_(line_width)
                arc.setLineCapStyle_(NSRoundLineCapStyle)
                self.colors[index % len(self.colors)].setStroke()
                arc.stroke()
                start_angle = end_angle

    def add_usage_bar(
        view: Any,
        label: str,
        percent: int | None,
        reset: str,
        x: float,
        y: float,
    ) -> None:
        color = quota_color(percent)
        text = make_label(label, 12, False)
        text.setTextColor_(card_secondary_text_color())
        text.setFrame_(NSMakeRect(x, y + 28, 70, 18))
        view.addSubview_(text)

        value = make_label("--" if percent is None else f"{percent}%", 12, True)
        value.setTextColor_(color)
        value.setFrame_(NSMakeRect(x + 116, y + 28, 36, 18))
        view.addSubview_(value)

        track_width = 142.0
        track = NSView.alloc().initWithFrame_(NSMakeRect(x, y + 17, track_width, 5))
        track.setWantsLayer_(True)
        track.layer().setCornerRadius_(2.5)
        track.layer().setBackgroundColor_(color.colorWithAlphaComponent_(0.16).CGColor())
        view.addSubview_(track)

        if percent is not None and percent > 0:
            fill_width = max(4.0, track_width * (min(percent, 100) / 100))
            fill = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, fill_width, 5))
            fill.setWantsLayer_(True)
            fill.layer().setCornerRadius_(2.5)
            fill.layer().setBackgroundColor_(color.CGColor())
            track.addSubview_(fill)

        reset_label = make_label(f"◷ {reset}", 11, False)
        reset_label.setTextColor_(card_muted_text_color())
        reset_label.setFrame_(NSMakeRect(x, y - 4, 142, 16))
        view.addSubview_(reset_label)

    def add_donut_legend_row(
        view: Any,
        *,
        color: Any,
        label: str,
        value: str,
        x: float,
        value_x: float,
        y: float,
    ) -> None:
        swatch = NSView.alloc().initWithFrame_(NSMakeRect(x, y + 3, 10, 10))
        swatch.setWantsLayer_(True)
        swatch.layer().setCornerRadius_(5)
        swatch.layer().setBackgroundColor_(color.CGColor())
        view.addSubview_(swatch)

        label_view = make_label(label, 13, True)
        label_view.setFrame_(NSMakeRect(x + 18, y - 1, value_x - x - 22, 18))
        view.addSubview_(label_view)

        value_view = make_label(value, 13, False)
        value_view.setAlignment_(1)
        value_view.setTextColor_(NSColor.secondaryLabelColor())
        value_view.setFrame_(NSMakeRect(value_x, y - 1, 50, 18))
        view.addSubview_(value_view)

    def add_refresh_button(view: Any, controller: Any, x: float, y: float) -> None:
        refresh = NSButton.buttonWithTitle_target_action_("Refresh Now", controller, "refreshNow:")
        refresh.setBordered_(False)
        refresh.setFrame_(NSMakeRect(x, y, 104, 20))
        view.addSubview_(refresh)

    def add_toggle_button(
        view: Any,
        controller: Any,
        title: str,
        x: float,
        y: float,
        *,
        button_width: float = 132,
    ) -> None:
        toggle = NSButton.buttonWithTitle_target_action_(title, controller, "toggleQuotaView:")
        toggle.setBordered_(False)
        toggle.setFrame_(NSMakeRect(x, y, button_width, 20))
        view.addSubview_(toggle)

    def make_status_badge(status_label: str) -> Any:
        color = status_color(status_label)
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 90, 24))
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(12)
        view.layer().setBackgroundColor_(color.colorWithAlphaComponent_(0.12).CGColor())
        view.layer().setBorderWidth_(1)
        view.layer().setBorderColor_(color.colorWithAlphaComponent_(0.28).CGColor())

        label = make_label(f"• {status_label}", 11, True)
        label.setAlignment_(2)
        label.setTextColor_(color)
        label.setFrame_(NSMakeRect(8, 4, 74, 16))
        view.addSubview_(label)
        return view

    def make_label(text: str, size: float, bold: bool) -> Any:
        label = NSTextField.labelWithString_(text)
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        label.setFont_(font)
        return label

    def card_background_color() -> Any:
        return NSColor.controlBackgroundColor()

    def card_border_color() -> Any:
        return NSColor.separatorColor().colorWithAlphaComponent_(0.55)

    def card_primary_text_color() -> Any:
        return NSColor.labelColor()

    def card_secondary_text_color() -> Any:
        return NSColor.secondaryLabelColor()

    def card_muted_text_color() -> Any:
        return NSColor.tertiaryLabelColor()

    def card_separator_color() -> Any:
        return NSColor.separatorColor().colorWithAlphaComponent_(0.75)

    def style_card_button(button: Any) -> None:
        if hasattr(button, "setContentTintColor_"):
            button.setContentTintColor_(card_secondary_text_color())

    def status_color(status_label: str) -> Any:
        if status_label == "Active":
            return NSColor.systemGreenColor()
        if status_label in {"Limited", "Exceeded"}:
            return NSColor.systemRedColor()
        if status_label == "Paused":
            return NSColor.systemOrangeColor()
        return NSColor.secondaryLabelColor()

    def quota_color(percent: int | None) -> Any:
        if percent is None:
            return NSColor.secondaryLabelColor()
        if percent >= 70:
            return NSColor.systemGreenColor()
        if percent >= 30:
            return NSColor.systemOrangeColor()
        return NSColor.systemRedColor()

    def donut_segment_colors() -> tuple[Any, ...]:
        return (
            NSColor.systemBlueColor(),
            NSColor.systemPurpleColor(),
            NSColor.systemGreenColor(),
            NSColor.systemOrangeColor(),
            NSColor.systemPinkColor(),
        )

    def format_menu_number(value: float) -> str:
        abs_value = abs(value)
        if abs_value >= 1_000_000:
            return f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
        if abs_value >= 1_000:
            return f"{value / 1_000:.2f}".rstrip("0").rstrip(".") + "K"
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def details_url(config: MenuBarConfig, card: AccountMenuCard) -> str:
        return config.base_url.rstrip("/") + card.details_path

    class MenuBarController(NSObject):
        def init(self) -> Any:
            self = objc_super(MenuBarController, self).init()
            if self is None:
                return None
            self.config = config
            self.runtime_options = runtime_options
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
            self.menu = NSMenu.alloc().init()
            self.status_item.setMenu_(self.menu)
            self.status_item.button().setTitle_("5h --")
            self._timer = None
            self._refresh_in_progress = False
            self._detail_urls = []
            self._runtime_status = None
            self._runtime_error = ""
            self._provider_sync_status = "Idle"
            self._provider_sync_error = ""
            self._provider_sync_in_progress = False
            self._start_on_launch_attempted = False
            self._quota_view_mode = "donut"
            self._last_snapshot = None
            self.applySnapshot_(MenuBarSnapshot(title="5h --", rows=(("Status", "Loading..."),)))
            return self

        def start(self) -> None:
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                float(self.config.refresh_interval_seconds),
                self,
                "refreshNow:",
                None,
                True,
            )
            if self.runtime_options is not None and self.runtime_options.start_on_launch:
                self._start_on_launch_attempted = True
                self.startServer_(None)
                return
            self.refreshNow_(None)

        def refreshNow_(self, _sender: object) -> None:
            if self._refresh_in_progress:
                return
            self._refresh_in_progress = True

            def worker() -> None:
                if self.runtime_options is not None:
                    status = status_from_options(self.runtime_options)
                    self._runtime_status = status
                    if not status.running:
                        call_after(self.applySnapshot_, stopped_runtime_snapshot(status))
                        return
                snapshot = fetch_menu_bar_snapshot(self.config)
                call_after(self.applySnapshot_, snapshot)

            Thread(target=worker, daemon=True).start()

        def openDashboard_(self, _sender: object) -> None:
            base_url = self.config.base_url
            if self._runtime_status is not None:
                base_url = self._runtime_status.dashboard_url
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(dashboard_page_url(base_url)))

        def openAccountDetails_(self, sender: Any) -> None:
            tag = int(sender.tag())
            if tag < 0 or tag >= len(self._detail_urls):
                return
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(self._detail_urls[tag]))

        def openLog_(self, _sender: object) -> None:
            if self._runtime_status is None:
                return
            NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(str(self._runtime_status.log_file)))

        def startServer_(self, _sender: object) -> None:
            if self.runtime_options is None or self._refresh_in_progress:
                return
            self._refresh_in_progress = True

            def worker() -> None:
                try:
                    self._runtime_error = ""
                    status = status_from_options(self.runtime_options)
                    if not status.running:
                        start_menu_bar_runtime(self.runtime_options)
                except Exception as exc:  # pragma: no cover - surfaced in menu UI
                    self._runtime_error = str(exc)
                finally:
                    self._refresh_in_progress = False
                    call_after(self.refreshNow_, None)

            Thread(target=worker, daemon=True).start()

        def stopServer_(self, _sender: object) -> None:
            if self.runtime_options is None or self._refresh_in_progress:
                return
            self._refresh_in_progress = True

            def worker() -> None:
                try:
                    self._runtime_error = ""
                    stop_menu_bar_runtime(self.runtime_options)
                except Exception as exc:  # pragma: no cover - surfaced in menu UI
                    self._runtime_error = str(exc)
                finally:
                    self._refresh_in_progress = False
                    call_after(self.refreshNow_, None)

            Thread(target=worker, daemon=True).start()

        def toggleQuotaView_(self, _sender: object) -> None:
            self._quota_view_mode = "bars" if self._quota_view_mode == "donut" else "donut"
            if self._last_snapshot is not None:
                self.applySnapshot_(self._last_snapshot)

        def quit_(self, _sender: object) -> None:
            NSApplication.sharedApplication().terminate_(None)

        def applySnapshot_(self, snapshot: MenuBarSnapshot) -> None:
            self._refresh_in_progress = False
            self._last_snapshot = snapshot
            self.status_item.button().setTitle_(snapshot.title)
            self.menu.removeAllItems()
            self._detail_urls = []
            can_show_donut = snapshot.primary_donut is not None
            show_bars = self._quota_view_mode == "bars" or not can_show_donut
            if show_bars:
                add_view_item(self.menu, make_quota_bars_header_view(self, can_show_donut=can_show_donut))
                for card in snapshot.account_cards:
                    add_view_item(self.menu, make_account_card_view(self, card, len(self._detail_urls)))
                    self._detail_urls.append(details_url(self.config, card))
                if snapshot.account_cards:
                    self.menu.addItem_(NSMenuItem.separatorItem())
                add_view_item(self.menu, make_overview_view(snapshot.rows, None, self))
            else:
                add_view_item(self.menu, make_overview_view(snapshot.rows, snapshot.primary_donut, self))
            if self.runtime_options is not None:
                self._runtime_status = status_from_options(self.runtime_options)
                self.menu.addItem_(NSMenuItem.separatorItem())
                add_view_item(self.menu, make_runtime_view(self._runtime_status, self._runtime_error))
                self.menu.addItem_(NSMenuItem.separatorItem())
                add_action(self, "Start Server", "startServer:")
                add_action(self, "Stop Server", "stopServer:")
                add_action(self, "Open Log", "openLog:")
            self.menu.addItem_(NSMenuItem.separatorItem())
            add_view_item(self.menu, make_provider_sync_view(self._provider_sync_status, self._provider_sync_error))
            add_action(self, "Sync Providers", "syncProviders:")
            self.menu.addItem_(NSMenuItem.separatorItem())
            add_action(self, "Open Dashboard", "openDashboard:")
            self.menu.addItem_(NSMenuItem.separatorItem())
            add_action(self, "Quit", "quit:")

        def syncProviders_(self, _sender: object) -> None:
            if self._provider_sync_in_progress:
                return
            self._provider_sync_in_progress = True
            self._provider_sync_status = "Running..."
            self._provider_sync_error = ""
            self.applySnapshot_(
                MenuBarSnapshot(
                    title=self.status_item.button().title(),
                    rows=(("Status", "Syncing..."),),
                )
            )

            def worker() -> None:
                try:
                    result = sync_codex_provider()
                    self._provider_sync_status = "Last sync OK" if result.succeeded else "Last sync failed"
                    self._provider_sync_error = "" if result.succeeded else result.message
                except Exception as exc:  # pragma: no cover - surfaced in menu UI
                    self._provider_sync_status = "Last sync failed"
                    self._provider_sync_error = str(exc)
                finally:
                    self._provider_sync_in_progress = False
                    call_after(self.refreshNow_, None)

            Thread(target=worker, daemon=True).start()

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = MenuBarController.alloc().init()
    app.setDelegate_(controller)
    controller.start()
    run_event_loop()
