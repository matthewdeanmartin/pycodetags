from pathlib import Path

import pluggy
from pycodetags_jinja_templates.views_templated import print_html

from pycodetags.collect import CollectedTODOs
from pycodetags.config import CodeTagsConfig

# Use the same marker name as defined in the host's hookspecs
hookimpl = pluggy.HookimplMarker("pycodetags")


@hookimpl
def code_tags_print_report(
    format_name: str, found_data: CollectedTODOs, output_path: str, config: CodeTagsConfig
) -> bool:
    if format_name == "html_pretty":
        print_html(found_data, output=Path(output_path))
        return True  # Indicates this plugin handled the request
    return False  # This plugin does not handle the requested format


@hookimpl
def code_tags_print_report_style_name() -> list[str]:
    return ["html_pretty"]
