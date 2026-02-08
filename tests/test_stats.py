from nomnom.stats import WatchStats


def test_watch_stats_counters() -> None:
    stats = WatchStats()

    stats.record_event()
    stats.record_event()
    stats.record_match("alpha")
    stats.record_match("alpha")
    stats.record_match("beta")
    stats.record_effect()
    stats.record_dry_run_effect()

    assert stats.events_processed == 2
    assert stats.effects_applied == 1
    assert stats.effects_skipped_dry_run == 1
    assert stats.plugin_match_counts == {"alpha": 2, "beta": 1}


def test_watch_stats_print_summary_calls_console_print() -> None:
    stats = WatchStats()
    printed: list[object] = []

    class StubConsole:
        def print(self, value) -> None:
            printed.append(value)

    stats.print_summary(StubConsole())

    assert len(printed) == 1
