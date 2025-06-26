import re

from pluggy import HookimplMarker

from pycodetags.config import CodeTagsConfig
from pycodetags.folk_code_tags import FolkTag

hookimpl = HookimplMarker("pycodetags")


class JavascriptFolkTagPlugin:
    @hookimpl
    def find_source_tags(self, file_path: str, config: CodeTagsConfig) -> list[FolkTag]:
        if not file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            return []

        found: list[FolkTag] = []

        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f):
                match = re.match(r"//\s*(TODO|FIXME)\s*(\((.*?)\))?:?\s*(.*)", line, re.IGNORECASE)
                if match:
                    tag = match.group(1).upper()
                    raw_person = match.group(3)
                    comment = match.group(4).strip()

                    folk: FolkTag = {
                        "file_path": file_path,
                        "line_number": idx + 1,
                        "code_tag": tag,
                        "comment": comment,
                        "custom_fields": {},
                        "original_text": line.strip(),
                    }
                    if raw_person:
                        folk["assignee"] = raw_person.strip()

                    found.append(folk)

        return found


javascript_plugin = JavascriptFolkTagPlugin()
