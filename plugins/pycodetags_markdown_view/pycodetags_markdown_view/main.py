# code_tags_markdown_view.py
import pluggy

from pycodetags.collect import CollectedTODOs
from pycodetags.config import CodeTagsConfig

# Use the same marker name as defined in the host's hookspecs
hookimpl = pluggy.HookimplMarker("pycodetags")


@hookimpl
def code_tags_print_report(
    format_name: str, found_data: CollectedTODOs, output_path: str, config: CodeTagsConfig
) -> bool:
    if format_name == "markdown_simple":
        print("# Simple Markdown Report")
        print("## TODOs")
        for todo in found_data.get("todos", []):
            if todo.is_probably_done():
                print(f"- [x] {todo.comment} (Closed: {todo.closed_date or 'N/A'})")
            else:
                print(f"- [ ] {todo.comment} (Assignee: {todo.assignee or 'N/A'}, Due: {todo.due or 'N/A'})")
        return True  # Indicates this plugin handled the request
    return False  # This plugin does not handle the requested format


@hookimpl
def code_tags_print_report_style_name() -> list[str]:
    return ["markdown_simple"]
