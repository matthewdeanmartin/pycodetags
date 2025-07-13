import re

from pluggy import HookimplMarker

from pycodetags import DataTag
from pycodetags.app_config.config import CodeTagsConfig

hookimpl = HookimplMarker("pycodetags")


class JavascriptFolkTagPlugin:
    @hookimpl
    def find_source_tags(
            self,
            file_path: str,
            # pylint: disable=unused-argument
            config: CodeTagsConfig,
    ) -> list[DataTag]:
        if not file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            return []

        found: list[DataTag] = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f):
                    match = re.match(r"//\s*(TODO|FIXME)\s*(\((.*?)\))?:?\s*(.*)", line, re.IGNORECASE)
                    if match:
                        tag = match.group(1).upper()
                        raw_person = match.group(3)
                        comment = match.group(4).strip()

                        folk: DataTag = {
                            "file_path": file_path,
                            "code_tag": tag,
                            "comment": comment,
                            "fields": {
                                "custom_fields": {},
                                "unprocessed_defaults": [],
                                "default_fields": {},
                                "data_fields": {},
                                "identity_fields": []
                            },
                            "original_text": line.strip(),
                            "offsets": (idx + 1, 1, 0, 0)
                        }
                        if raw_person:
                            folk["fields"]["custom_fields"]["assignee"] = raw_person.strip()

                        found.append(folk)
        except PermissionError as pe:
            print(f"PermissionError: Could not read file {file_path}. Error: {pe}")
            return []
        except FileNotFoundError as fnfe:
            print(f"FileNotFoundError: Could not find file {file_path}. Error: {fnfe}")
            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error reading file {file_path}: {e}")
            return []

        return found


javascript_plugin = JavascriptFolkTagPlugin()
