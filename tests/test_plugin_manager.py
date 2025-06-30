import pycodetags.plugin_manager as pm


def test_basics():
    # Not really good candidates for unit tests.
    assert pm.get_plugin_manager()
    pm.reset_plugin_manager()
