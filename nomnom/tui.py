import logging
import psutil
import threading
from datetime import datetime
from typing import Any, Callable

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Static, RichLog
from textual import work
from textual.reactive import reactive
from rich.text import Text
from rich.markup import escape

from nomnom.config import Config
from nomnom.events import FileEvent, EventType
from nomnom.plugin import Plugin
from nomnom.stats import WatchStats
from nomnom.watcher import run_watcher


class EffectLogHandler(logging.Handler):
    def __init__(self, write_callback: Callable[[str], None]):
        super().__init__()
        self.write_callback = write_callback
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)

            # Basic styling based on log level or content
            now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            if record.levelno >= logging.ERROR:
                level_str = "[bold red][ERROR][/]"
            elif record.levelno >= logging.WARNING:
                level_str = "[bold yellow][WARN][/]"
            elif "Would execute" in msg or "[DRY RUN]" in msg:
                level_str = "[bold #ffb86c][DRYRUN][/]"
                msg = msg.replace("[DRY RUN]", "").strip()
            elif "matched" in msg:
                level_str = "[bold #8be9fd][INFO][/]"
            elif "Simulated action complete" in msg or "[SUCCESS]" in msg:
                level_str = "[bold #50fa7b][SUCCESS][/]"
            else:
                level_str = "[bold #8be9fd][INFO][/]"

            formatted_msg = f"[#6272a4]{now}[/] {level_str} {escape(msg)}"
            self.write_callback(formatted_msg)
        except Exception:
            self.handleError(record)


class KPIBox(Static):
    title = reactive("")
    value = reactive("0")
    subtext = reactive("")

    def __init__(self, title: str, value: str = "0", subtext: str = "", id: str | None = None, classes: str | None = None):
        super().__init__(id=id, classes=classes)
        self.title = title
        self.value = value
        self.subtext = subtext

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="kpi-title")
        yield Label(self.value, classes="kpi-value kpi-val-cls")
        yield Label(self.subtext, classes="kpi-sub kpi-sub-cls")

    def watch_value(self, value: str) -> None:
        try:
            self.query_one(".kpi-val-cls", Label).update(value)
        except Exception:
            pass

    def watch_subtext(self, subtext: str) -> None:
        try:
            self.query_one(".kpi-sub-cls", Label).update(subtext)
        except Exception:
            pass


class NomnomTUI(App):
    CSS_PATH = "tui.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    uptime_start = datetime.now()
    stats: WatchStats
    stop_event: threading.Event

    def __init__(self, config: Config, plugins: list[tuple[str, Plugin]], dry_run: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.plugins = plugins
        self.dry_run = dry_run
        self.stats = WatchStats()
        self.stop_event = threading.Event()

    def compose(self) -> ComposeResult:
        yield Footer()

        with Horizontal():
            with Vertical(id="sidebar"):
                with Horizontal(id="sidebar-header"):
                    yield Label(">_ ", classes="logo-icon")
                    yield Label("nomnom ", id="logo")
                    yield Label("v0.1.0", id="version")

                with Vertical(id="sidebar-content"):
                    yield Label("WATCH GROUPS", classes="section-title")
                    for wg in self.config.watch_groups:
                        with Horizontal(classes="sidebar-item"):
                            yield Label(f"/{wg.name}")
                            yield Label("●", classes="status-dot green")

                    yield Label("ACTIVE PLUGINS", classes="section-title")
                    for p in self.config.plugins:
                        with Horizontal(classes="sidebar-item"):
                            yield Label(p.name)
                            yield Label("ON", classes="status-dot green")

            with Vertical(id="main-area"):
                with Horizontal(id="header-badges"):
                    if self.dry_run:
                        yield Label("DRY RUN ACTIVE", classes="badge red")
                    yield Label("UPTIME: 00:00:00", id="uptime-badge", classes="badge green")
                    yield Label("MEM: 0MB", id="mem-badge", classes="badge green")

                with Vertical(id="content"):
                    with Horizontal(id="kpis"):
                        yield KPIBox("EVENTS (FS TRIGGERS)", "0", "+0/min", id="kpi-events", classes="kpi-box")
                        yield KPIBox("MATCHES (RULE HITS)", "0", "0% hit rate", id="kpi-matches", classes="kpi-box")

                        actions_subtext = "Dry Run Active" if self.dry_run else ""
                        yield KPIBox("ACTIONS EXECUTED", "0", actions_subtext, id="kpi-actions", classes="kpi-box")

                    with Vertical(id="event-feed-section"):
                        with Horizontal(classes="section-header"):
                            yield Label("EVENT FEED ", classes="section-header-title")
                            yield Label("(Raw FS Activity)", classes="section-header-sub")

                        yield DataTable(id="event-table")

                    with Vertical(id="effect-log-section"):
                        with Horizontal(classes="section-header"):
                            yield Label("EFFECT LOG ", classes="section-header-title")
                            yield Label("(Plugin Results)", classes="section-header-sub")

                        yield RichLog(id="effect-log", wrap=True, markup=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Timestamp", "Event", "Type", "Path")
        table.cursor_type = "row"

        self.update_stats()
        self.set_interval(1.0, self.update_stats)

        log_handler = EffectLogHandler(self.log_effect)
        log_handler.setLevel(logging.INFO)
        logging.getLogger("nomnom.dispatcher").addHandler(log_handler)

        self.start_watcher()

    def update_stats(self) -> None:
        uptime = datetime.now() - self.uptime_start
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.query_one("#uptime-badge", Label).update(f"UPTIME: {hours:02d}:{minutes:02d}:{seconds:02d}")

        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
        self.query_one("#mem-badge", Label).update(f"MEM: {int(mem_mb)}MB")

        self.query_one("#kpi-events", KPIBox).value = str(self.stats.events_processed)
        total_matches = sum(self.stats.plugin_match_counts.values())
        self.query_one("#kpi-matches", KPIBox).value = str(total_matches)

        hit_rate = (total_matches / self.stats.events_processed * 100) if self.stats.events_processed > 0 else 0
        self.query_one("#kpi-matches", KPIBox).subtext = f"{hit_rate:.0f}% hit rate"

        actions = self.stats.effects_applied
        self.query_one("#kpi-actions", KPIBox).value = str(actions)

    def log_effect(self, message: str) -> None:
        self.call_from_thread(self._write_log, message)

    def _write_log(self, message: str) -> None:
        rich_log = self.query_one(RichLog)
        rich_log.write(message)

    def on_file_event(self, event: FileEvent) -> None:
        self.call_from_thread(self._add_event_to_table, event)

    def _add_event_to_table(self, event: FileEvent) -> None:
        table = self.query_one(DataTable)

        timestamp = event.created_at.strftime("%H:%M:%S.%f")[:-3]

        if event.event_type == EventType.CREATED:
            event_str = Text("CREATE", style="bold #8be9fd")
        elif event.event_type == EventType.MODIFIED:
            event_str = Text("MODIFY", style="bold #bd93f9")
        elif event.event_type == EventType.DELETED:
            event_str = Text("DELETE", style="bold #ff5555")
        else:
            event_str = Text(event.event_type.value.upper())

        is_dir = event.path.is_dir()
        type_str = Text("Dir" if is_dir else "File", style="#f8f8f2")

        path_str = Text(str(event.path), style="#f8f8f2")

        table.add_row(timestamp, event_str, type_str, path_str)
        table.scroll_end(animate=False)

    def action_quit(self) -> None:
        self.stop_event.set()
        self.exit()

    @work(thread=True)
    def start_watcher(self) -> None:
        run_watcher(
            cfg=self.config,
            plugins=self.plugins,
            console=None,
            dry_run=self.dry_run,
            once=False,
            once_watch_group=None,
            on_event=self.on_file_event,
            stats=self.stats,
            stop_event=self.stop_event
        )
