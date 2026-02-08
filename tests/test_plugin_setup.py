from nomnom.plugin import has_setup, run_plugin_setup


class PluginWithSetup:
    def __init__(self) -> None:
        self.setup_called = False

    def matches(self, event) -> bool:
        return False

    def handle(self, event) -> list:
        return []

    def setup(self) -> None:
        self.setup_called = True


class PluginWithoutSetup:
    def matches(self, event) -> bool:
        return False

    def handle(self, event) -> list:
        return []


class PluginWithNonCallableSetup:
    setup = "not-callable"

    def matches(self, event) -> bool:
        return False

    def handle(self, event) -> list:
        return []


def test_has_setup_detects_only_callable_setup_method() -> None:
    assert has_setup(PluginWithSetup()) is True
    assert has_setup(PluginWithoutSetup()) is False
    assert has_setup(PluginWithNonCallableSetup()) is False


def test_run_plugin_setup_calls_setup_when_available() -> None:
    plugin = PluginWithSetup()

    run_plugin_setup(plugin)

    assert plugin.setup_called is True


def test_run_plugin_setup_noops_without_callable_setup() -> None:
    run_plugin_setup(PluginWithoutSetup())
    run_plugin_setup(PluginWithNonCallableSetup())
