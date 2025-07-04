# code_tags_markdown_view.py
import pluggy

from pycodetags import DATA
from pycodetags.config import CodeTagsConfig

# Use the same marker name as defined in the host's hookspecs
hookimpl = pluggy.HookimplMarker("pycodetags")


@hookimpl
def print_report(
    format_name: str,
    found_data: list[DATA],
    # pylint: disable=unused-argument
    output_path: str,
    # pylint: disable=unused-argument
    config: CodeTagsConfig,
) -> bool:
    return False
    # raise NotImplementedError()
    # return False  # This plugin does not handle the requested format


@hookimpl
def print_report_style_name() -> list[str]:
    return ["markdown_simple"]
