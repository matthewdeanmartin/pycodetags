"""
Tool for plugin developers
"""

import pluggy


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
