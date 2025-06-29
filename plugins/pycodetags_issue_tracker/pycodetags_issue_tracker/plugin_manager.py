import logging

import pluggy
from pycodetags_issue_tracker.plugin_specs import IssueTrackerSpec

logger = logging.getLogger(__name__)

PM: pluggy.PluginManager = pluggy.PluginManager("pycodetags")


def set_plugin_manager(new_pm: pluggy.PluginManager) -> None:
    """For testing or events can double up"""
    # pylint: disable=global-statement
    global PM  # nosec # noqa
    PM = new_pm
    PM.add_hookspecs(IssueTrackerSpec)
    count = PM.load_setuptools_entrypoints("pycodetags_issue_tracker")
    logger.info(f"Found {count} plugins for pycodetags_issue_tracker")


if logger.isEnabledFor(logging.DEBUG):
    # magic line to set a writer function
    PM.trace.root.setwriter(print)
    undo = PM.enable_tracing()


# At class level or module-level:
def get_plugin_manager() -> pluggy.PluginManager:
    return PM
