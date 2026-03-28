from pathlib import Path

import pytest

from nomnom.dispatcher import dispatch
from nomnom.effects import CreateFile, EmitEvent
from nomnom.events import EventType
from nomnom.stats import WatchStats


def test_dispatch_calls_matching_plugin(make_event, stub_plugin_cls) -> None:
    event = make_event()
    plugin = stub_plugin_cls(matches_result=True, effects=[])

    dispatch(event, [("stub", plugin)], stats=WatchStats())

    assert plugin.matched_events == [event]
    assert plugin.handled_events == [event]


def test_dispatch_skips_non_matching_plugin(make_event, stub_plugin_cls) -> None:
    event = make_event()
    plugin = stub_plugin_cls(matches_result=False, effects=[])

    dispatch(event, [("stub", plugin)], stats=WatchStats())

    assert plugin.matched_events == [event]
    assert plugin.handled_events == []


def test_dispatch_executes_effects(
    monkeypatch: pytest.MonkeyPatch, make_event, stub_plugin_cls
) -> None:
    event = make_event()
    effect = CreateFile(path=Path("/tmp/out.txt"), content=b"hello")
    plugin = stub_plugin_cls(matches_result=True, effects=[effect])
    executed: list[object] = []

    def fake_execute(effect_obj) -> None:
        executed.append(effect_obj)

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", fake_execute)

    dispatch(event, [("stub", plugin)], stats=WatchStats())

    assert executed == [effect]


def test_dispatch_recurses_on_emit_event(
    monkeypatch: pytest.MonkeyPatch, make_event, stub_plugin_cls
) -> None:
    first = make_event(path=Path("/tmp/first.txt"))
    second = make_event(event_type=EventType.MODIFIED, path=Path("/tmp/second.txt"))

    plugin = stub_plugin_cls(matches_result=True, effects=[EmitEvent(event=second)])
    calls: list[Path] = []

    def fake_execute(_effect) -> None:
        calls.append(Path("/tmp/executed"))

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", fake_execute)

    dispatch(first, [("stub", plugin)], max_depth=3, stats=WatchStats())

    assert plugin.handled_events == [first, second, second]
    assert calls == []


def test_dispatch_respects_max_depth(
    caplog: pytest.LogCaptureFixture, make_event, stub_plugin_cls
) -> None:
    """A plugin that always emits should be capped at max_depth generations."""
    event = make_event()
    inner = make_event(event_type=EventType.MODIFIED, path=Path("/tmp/inner.txt"))
    plugin = stub_plugin_cls(matches_result=True, effects=[EmitEvent(event=inner)])

    caplog.set_level("WARNING")
    dispatch(event, [("stub", plugin)], max_depth=2, stats=WatchStats())

    # depth 0: event processed, emits inner
    # depth 1: inner processed, emits inner again
    # depth 2: max_depth reached, dropped
    assert plugin.handled_events == [event, inner]
    assert "Max event depth (2) reached" in caplog.text


def test_dispatch_isolates_matches_crash(
    caplog: pytest.LogCaptureFixture, make_event, stub_plugin_cls
) -> None:
    event = make_event()

    class CrashingMatchesPlugin:
        def matches(self, _event):
            raise RuntimeError("boom")

        def handle(self, _event):
            return []

    healthy = stub_plugin_cls(matches_result=True, effects=[])
    caplog.set_level("ERROR")

    dispatch(event, [("crashy", CrashingMatchesPlugin()), ("healthy", healthy)], stats=WatchStats())

    assert healthy.handled_events == [event]
    assert "crashed in matches()" in caplog.text


def test_dispatch_isolates_handle_crash(
    caplog: pytest.LogCaptureFixture, make_event, stub_plugin_cls
) -> None:
    event = make_event()

    class CrashingHandlePlugin:
        def matches(self, _event):
            return True

        def handle(self, _event):
            raise RuntimeError("boom")

    healthy = stub_plugin_cls(matches_result=True, effects=[])
    caplog.set_level("ERROR")

    dispatch(event, [("crashy", CrashingHandlePlugin()), ("healthy", healthy)], stats=WatchStats())

    assert healthy.handled_events == [event]
    assert "crashed in handle()" in caplog.text


def test_dispatch_isolates_effect_crash(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    make_event,
    stub_plugin_cls,
) -> None:
    event = make_event()
    bad_effect = CreateFile(path=Path("/tmp/bad.txt"), content=b"bad")
    good_effect = CreateFile(path=Path("/tmp/good.txt"), content=b"good")
    plugin = stub_plugin_cls(matches_result=True, effects=[bad_effect, good_effect])
    executed: list[object] = []

    def fake_execute(effect_obj) -> None:
        if effect_obj is bad_effect:
            raise RuntimeError("effect failed")
        executed.append(effect_obj)

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", fake_execute)
    caplog.set_level("ERROR")

    dispatch(event, [("stub", plugin)], stats=WatchStats())

    assert executed == [good_effect]
    assert "Effect CreateFile failed" in caplog.text


def test_dispatch_processes_plugins_in_order(make_event) -> None:
    event = make_event()
    order: list[str] = []

    class OrderedPlugin:
        def __init__(self, name: str):
            self.name = name

        def matches(self, _event):
            return True

        def handle(self, _event):
            order.append(self.name)
            return []

    dispatch(
        event,
        [("first", OrderedPlugin("first")), ("second", OrderedPlugin("second"))],
        stats=WatchStats(),
    )

    assert order == ["first", "second"]


def test_dispatch_dry_run_skips_executor(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    make_event,
    stub_plugin_cls,
) -> None:
    event = make_event()
    effect = CreateFile(path=Path("/tmp/out.txt"), content=b"hello")
    plugin = stub_plugin_cls(matches_result=True, effects=[effect])
    called = False

    def fake_execute(_effect_obj) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", fake_execute)
    caplog.set_level("INFO")

    dispatch(event, [("stub", plugin)], dry_run=True, stats=WatchStats())

    assert called is False
    assert "[DRY RUN]" in caplog.text


def test_dispatch_dry_run_recurses_emit_event(
    monkeypatch: pytest.MonkeyPatch,
    make_event,
    stub_plugin_cls,
) -> None:
    first = make_event(path=Path("/tmp/first.txt"))
    second = make_event(event_type=EventType.MODIFIED, path=Path("/tmp/second.txt"))

    plugin = stub_plugin_cls(matches_result=True, effects=[EmitEvent(event=second)])
    called = False

    def fake_execute(_effect_obj) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", fake_execute)

    dispatch(first, [("stub", plugin)], max_depth=3, dry_run=True, stats=WatchStats())

    assert plugin.handled_events == [first, second, second]
    assert called is False


def test_dispatch_records_stats_for_matches_and_effects(
    monkeypatch: pytest.MonkeyPatch, make_event, stub_plugin_cls
) -> None:
    event = make_event()
    effect = CreateFile(path=Path("/tmp/out.txt"), content=b"hello")
    plugin = stub_plugin_cls(matches_result=True, effects=[effect])
    stats = WatchStats()

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", lambda _effect: True)

    dispatch(event, [("stub", plugin)], stats=stats)

    assert stats.events_processed == 1
    assert stats.plugin_match_counts == {"stub": 1}
    assert stats.effects_applied == 1


def test_dispatch_records_stats_for_emitted_events(
    make_event, stub_plugin_cls
) -> None:
    first = make_event(path=Path("/tmp/first.txt"))
    second = make_event(event_type=EventType.MODIFIED, path=Path("/tmp/second.txt"))
    plugin = stub_plugin_cls(matches_result=True, effects=[EmitEvent(event=second)])
    stats = WatchStats()

    dispatch(first, [("stub", plugin)], stats=stats, max_depth=3)

    assert stats.events_processed == 3


def test_dispatch_does_not_count_noop_effects_as_applied(
    monkeypatch: pytest.MonkeyPatch, make_event, stub_plugin_cls
) -> None:
    from nomnom.executor import EffectSkipped

    event = make_event()
    effect = CreateFile(path=Path("/tmp/out.txt"), content=b"hello")
    plugin = stub_plugin_cls(matches_result=True, effects=[effect])
    stats = WatchStats()

    def raise_effect_skipped(_effect):
        raise EffectSkipped()

    monkeypatch.setattr("nomnom.dispatcher.executor.execute", raise_effect_skipped)

    dispatch(event, [("stub", plugin)], stats=stats)

    assert stats.effects_applied == 0
