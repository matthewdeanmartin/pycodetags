from __future__ import annotations

import datetime
import logging
from typing import Any

from pycodetags.data_tags_schema import DataTag, DataTagSchema

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


def promote_fields(tag: DataTag, data_tag_schema: DataTagSchema) -> None:
    fields = tag["fields"]
    if fields["unprocessed_defaults"]:
        for value in fields.get("unprocessed_defaults", []):
            consumed = False
            for the_type, the_name in data_tag_schema["default_fields"].items():
                if the_type == "int" and not fields["data_fields"].get(the_name) and not consumed:
                    try:
                        fields["data_fields"][the_name] = int(value)
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to int")
                elif the_type == "date" and not fields["data_fields"].get(the_name) and not consumed:
                    try:
                        fields["data_fields"][the_name] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to datetime")
                elif the_type == "str" and not fields["data_fields"].get(the_name) and not consumed:
                    fields["data_fields"][the_name] = value
                    consumed = True

    if not fields.get("custom_fields", {}) and not fields.get("default_fields", {}):
        # nothing to promote
        return

    # It is already there, just move it over.
    for default_key, default_value in tag["fields"]["default_fields"].items():
        if default_key in fields["data_fields"] and fields["data_fields"][default_key] != default_value:
            # Strict?
            logger.warning(
                "Field in both data_fields and default_fields and they don't match: "
                f'{default_key}: {fields["data_fields"][default_key]} != {default_value}'
            )

            # # This only handles strongly type DATA() or TODO(). Comment tags are all strings!
            # if isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, list):
            #     fields["data_fields"][default_key].extend(default_value)
            # elif isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, str):
            #     fields["data_fields"][default_key].append(default_value)
            # elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, list):
            #     fields["data_fields"][default_key] = default_value + [fields["data_fields"][default_key]]
            # elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, str):
            #     # promotes str to list[str], ugly!
            #     fields["data_fields"][default_key] = [fields["data_fields"][default_key], default_value]

        else:
            fields["data_fields"][default_key] = default_value

    # promote a custom_field to root field if it should have been a root field.
    field_aliases: dict[str, str] = data_tag_schema["data_field_aliases"]
    # putative custom field, is it actually standard?
    for custom_field, custom_value in fields["custom_fields"].copy().items():
        if custom_field in field_aliases:
            # Okay, found a custom field that should have been standard
            full_alias = field_aliases[custom_field]

            if fields["data_fields"].get(full_alias):
                # found something already there
                consumed = False
                if isinstance(fields["data_fields"][full_alias], list):
                    # root is list
                    if isinstance(custom_value, list):
                        # both are list: merge list into parent list
                        fields["data_fields"][full_alias].extend(custom_value)
                        consumed = True
                    elif isinstance(custom_value, str):
                        # list/string promote parent string to list (ugh!)
                        fields["data_fields"][full_alias] = fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                    else:
                        # list/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                elif isinstance(fields["data_fields"][full_alias], str):
                    if isinstance(custom_value, list):
                        # str/list: parent str joins custom list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias]] + custom_value
                        consumed = True
                    elif isinstance(custom_value, str):
                        # str/str forms a list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias], custom_value]
                        consumed = True
                    else:
                        # str/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias],
                            custom_value,
                        ]  # xtype: ignore
                        consumed = True
                else:
                    # surprise/surprise = > list
                    logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                    fields[full_alias] = [fields[full_alias], custom_value]  # type: ignore
                    consumed = True
                if consumed:
                    del fields["custom_fields"][custom_field]
                else:
                    # This might not  be reachable.
                    logger.warning(f"Failed to promote custom_field {full_alias}/{custom_value}, not consumed")


def merge_two_dicts(x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z
