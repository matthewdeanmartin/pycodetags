"""Read standalone JavaScript/TypeScript line comments using an explicit core schema."""

import re
from pathlib import Path

from pluggy import HookimplMarker

from pycodetags.data_tags.formats import parse_block
from pycodetags.python.comment_finder import extract_comment_lines
from pycodetags.schemas import resolve_schema

hookimpl = HookimplMarker("pycodetags")


class JavascriptTagPlugin:
    """Recognize standalone // blocks; no string-literal or inline-comment guessing."""

    @hookimpl
    def find_source_tags(self, file_path, config):
        if not file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            return []
        path = Path(file_path)
        schema = resolve_schema(config.schema_for_path(path), path)
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        found = []
        block = []
        first = 0
        for number, line in enumerate(lines + [""]):
            if re.match(r"^[ \t]*//", line):
                if not block:
                    first = number
                block.append(line.replace("//", "#", 1))
                continue
            if block:
                for tag in parse_block("".join(block), schema):
                    start, column, end, end_column = tag["offsets"]
                    tag["offsets"] = (first + start, column, first + end, end_column + 1)
                    tag["original_text"] = extract_comment_lines(lines, tag["offsets"])
                    tag["file_path"] = str(path.resolve())
                    tag["schema"] = schema
                    found.append(tag)
                block = []
        return found


javascript_plugin = JavascriptTagPlugin()
