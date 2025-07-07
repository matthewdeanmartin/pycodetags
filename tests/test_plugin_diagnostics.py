from unittest.mock import Mock, create_autospec

import pycodetags.plugin_manager as pd


def test_no_plugins_loaded(capsys):
    pm = create_autospec("pluggy.PluginManager", instance=True)
    pm.get_plugins = Mock()
    pm.get_plugins.return_value = []


    pd.plugin_currently_loaded(pm)

    out = capsys.readouterr().out
    assert "--- Loaded pycodetags Plugins ---" in out
    assert "No plugins currently loaded." in out
    assert "------------------------------" in out


def test_single_plugin_not_blocked_with_hook(capsys):
    plugin = object()
    pm = create_autospec("pluggy.PluginManager", instance=True)

    # Setup mock returns
    pm.get_plugins = Mock()
    pm.get_plugins.return_value = [plugin]
    pm.get_canonical_name = Mock()
    pm.get_canonical_name.return_value = "mock_plugin"
    pm.is_blocked = Mock()
    pm.is_blocked.return_value = False

    # Create mock hook caller and hookimpls
    mock_hookimpl = Mock()
    mock_hookimpl.get_hookimpls.return_value = [plugin]

    pm.hook = Mock()
    pm.hook.__dict__ = {
        "some_hook": mock_hookimpl,
        "_internal": Mock(),  # should be skipped
    }

    pd.plugin_currently_loaded(pm)

    out = capsys.readouterr().out
    assert "- mock_plugin" in out
    assert "  - Implements hook: some_hook" in out
    assert "(BLOCKED)" not in out


def test_plugin_blocked_and_no_hooks(capsys):
    plugin = object()
    pm = create_autospec("pluggy.PluginManager", instance=True)

    pm.get_plugins = Mock()
    pm.get_plugins.return_value = [plugin]
    pm.get_canonical_name = Mock()
    pm.get_canonical_name.return_value = "blocked_plugin"
    pm.is_blocked = Mock()
    pm.is_blocked.return_value = True

    # Hooks return empty impl list
    empty_hook = Mock()
    empty_hook.get_hookimpls.return_value = []

    pm.hook = Mock()
    pm.hook.__dict__ = {"hook_a": empty_hook}

    pd.plugin_currently_loaded(pm)

    out = capsys.readouterr().out
    assert "- blocked_plugin (BLOCKED)" in out
    assert "Implements hook" not in out
