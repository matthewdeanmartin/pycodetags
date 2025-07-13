"""
The pluggy plugin manager that finds plugins and invokes them when needed.
"""

import logging

import pluggy

from pycodetags.plugin_specs import CodeTagsSpec

logger = logging.getLogger(__name__)

PM = pluggy.PluginManager("pycodetags")
PM.add_hookspecs(CodeTagsSpec)
# PM.set_blocked("malicious_plugin")
PLUGIN_COUNT = PM.load_setuptools_entrypoints("pycodetags")
logger.info(f"Found {PLUGIN_COUNT} plugins")


def reset_plugin_manager() -> None:
    """For testing or events can double up"""
    # pylint: disable=global-statement
    global PM  # nosec # noqa
    PM = pluggy.PluginManager("pycodetags")
    PM.add_hookspecs(CodeTagsSpec)
    PM.load_setuptools_entrypoints("pycodetags")


if logger.isEnabledFor(logging.DEBUG):
    # magic line to set a writer function
    PM.trace.root.setwriter(print)
    undo = PM.enable_tracing()


# At class level or module-level:
def get_plugin_manager() -> pluggy.PluginManager:
    """Interface to help with unit testing"""
    return PM


def plugin_currently_loaded(pm: pluggy.PluginManager) -> None:
    """List plugins in memory"""
    print("--- Loaded pycodetags Plugins ---")
    loaded_plugins = pm.get_plugins()  #
    if not loaded_plugins:
        print("No plugins currently loaded.")
    else:
        for plugin in loaded_plugins:
            plugin_name = pm.get_canonical_name(plugin)  #
            blocked_status = " (BLOCKED)" if pm.is_blocked(plugin_name) else ""  #
            print(f"- {plugin_name}{blocked_status}")

            # Optional: print more detailed info about hooks implemented by this plugin
            # For each hookspec, list if this plugin implements it
            for hook_name in pm.hook.__dict__:
                if hook_name.startswith("_"):  # Skip internal attributes
                    continue
                hook_caller = getattr(pm.hook, hook_name)
                if (
                    plugin in hook_caller.get_hookimpls()
                ):  # Check if this specific plugin has an implementation for this hook
                    print(f"  - Implements hook: {hook_name}")

    print("------------------------------")
