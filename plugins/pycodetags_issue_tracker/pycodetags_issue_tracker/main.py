"""
Register plugin hooks
"""
import argparse

import pluggy
from pluggy import HookimplMarker
from pycodetags_issue_tracker.plugin_manager import set_plugin_manager

hookimpl = HookimplMarker("pycodetags")


class IssueTrackerApp:
    @hookimpl
    def register_app(self, pm: pluggy.PluginManager, parser:argparse.ArgumentParser)->bool:
        set_plugin_manager(new_pm=pm)
        # TODO: register issue tracker specific commands, e.g. remove DONE
        return True


issue_tracker_app_plugin = IssueTrackerApp()
