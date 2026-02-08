from dataclasses import dataclass, field
from time import monotonic

from rich.table import Table


@dataclass
class WatchStats:
    start_time: float = field(default_factory=monotonic)
    events_processed: int = 0
    effects_applied: int = 0
    effects_skipped_dry_run: int = 0
    plugin_match_counts: dict[str, int] = field(default_factory=dict)

    def record_event(self) -> None:
        self.events_processed += 1

    def record_match(self, name: str) -> None:
        self.plugin_match_counts[name] = self.plugin_match_counts.get(name, 0) + 1

    def record_effect(self) -> None:
        self.effects_applied += 1

    def record_dry_run_effect(self) -> None:
        self.effects_skipped_dry_run += 1

    def print_summary(self, console) -> None:
        duration = monotonic() - self.start_time

        table = Table(title="Watch Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta", justify="right")

        table.add_row("Duration (seconds)", f"{duration:.2f}")
        table.add_row("Events processed", str(self.events_processed))
        table.add_row("Effects applied", str(self.effects_applied))
        table.add_row("Effects skipped (dry-run)", str(self.effects_skipped_dry_run))

        if self.plugin_match_counts:
            for name, count in sorted(self.plugin_match_counts.items()):
                table.add_row(f"Plugin matches: {name}", str(count))

        console.print(table)
