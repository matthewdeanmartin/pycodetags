from __future__ import annotations

import datetime
import logging
from typing import Any

import jmespath
from jmespath.functions import Functions
from jmespath.visitor import Options

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_schema import DataTagFields, DataTagSchema, FieldInfo
from pycodetags.data_tags.meta_builder import build_meta_object

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


class DataTag(TypedDict, total=False):
    """An abstract data code tag."""

    code_tag: str
    comment: str
    fields: DataTagFields

    # metadata
    file_path: str | None
    original_text: str | None
    """Source code before parsing"""

    original_schema: str | None
    """Pep350 or Folk"""

    offsets: tuple[int, int, int, int] | None
    """Start line, start character, end line, end character"""


def convert_data_tag_to_data_object(tag_value: DataTag, schema: DataTagSchema) -> DATA:
    """
    Convert a DataTag dict to a DATA object.

    Args:
        tag_value (DataTag): The PEP350Tag to convert.
        schema (DataTagSchema): Schema for DataTag
    """
    # default fields should have already been promoted to data_fields by now.
    kwargs = upgrade_to_specific_schema(tag_value, schema)

    return DATA(**kwargs)  # xtype: ignore[arg-type]


def upgrade_to_specific_schema(tag_value: DataTag, schema: DataTagSchema, flat: bool = True) -> dict[str, Any]:
    """Convert a DataTag to a specific schema.

    Args:
        tag_value (DataTag): The DataTag to convert.
        schema (DataTagSchema): The schema to use for the conversion.
        flat (bool): If True, return a flat dict, otherwise return a nested dict.

    Returns:
        dict[str, Any]: A dictionary representation of the DataTag with fields promoted according to the schema.
    """
    data_fields = tag_value["fields"]["data_fields"]
    custom_fields = tag_value["fields"]["custom_fields"]
    final_data = {}
    final_custom = {}
    for found, value in data_fields.items():
        if found in schema["data_fields"]:
            final_data[found] = value
        else:
            final_custom[found] = value
    for found, value in custom_fields.items():
        if found in schema["data_fields"]:
            if found in final_data:
                logger.warning("Found same field in both data and custom")
            final_data[found] = value
        else:
            if found in final_custom:
                logger.warning("Found same field in both data and custom")
            final_custom[found] = value
    kwargs: DataTag | dict[str, Any] = {
        "code_tag": tag_value["code_tag"],
        "comment": tag_value["comment"],
        # Source Mapping
        "file_path": tag_value.get("file_path"),
        "original_text": tag_value.get("original_text"),
        "original_schema": "pep350",
        "offsets": tag_value.get("offsets"),
    }
    if flat:
        kwargs["default_fields"] = tag_value["fields"]["default_fields"]  # type:ignore[typeddict-unknown-key]
        kwargs["data_fields"] = final_data  # type:ignore[typeddict-unknown-key]
        kwargs["custom_fields"] = final_custom  # type:ignore[typeddict-unknown-key]
        ud = tag_value["fields"]["unprocessed_defaults"]
        kwargs["unprocessed_defaults"] = ud  # type:ignore[typeddict-unknown-key]
        # kwargs["identity_fields"]=tag_value["fields"].get("identity_fields", {})  # type:ignore[typeddict-unknown-key]
    else:
        kwargs["fields"] = {
            "data_fields": final_data,
            "custom_fields": final_custom,
            "default_fields": tag_value["fields"]["default_fields"],
            "unprocessed_defaults": tag_value["fields"]["unprocessed_defaults"],
            "identity_fields": tag_value["fields"].get("identity_fields", []),
        }
        promote_fields(kwargs, schema)  # type: ignore[arg-type]
    return kwargs  # type: ignore[return-value]


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

    # jmespath processing
    meta = build_meta_object(tag.get("file_path"))
    initialize_fields_from_schema(tag, meta, data_tag_schema["field_infos"], is_new=False)


def merge_two_dicts(x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z


class ExpressionEvaluationError(Exception):
    pass


class CodeTagsCustomFunctions(Functions):
    """Custom JMESPath functions for pycodetags."""

    @jmespath.functions.signature({"types": ["object"]}, {"types": []})
    def _func_lookup(self, dictionary: dict, key: Any) -> Any:
        """
        Performs a dynamic key lookup in a dictionary.
        Allows expressions like lookup(my.dict, my.key_name).
        """
        return dictionary.get(key)


def evaluate_field_expression(expr: str | None, *, tag: DataTag, meta: dict) -> Any:
    """
    Evaluate a JMESPath expression using the combined context of the tag and metadata.

    Parameters:
        expr: The JMESPath expression from the FieldInfo (e.g. value_on_new).
        tag: The structured JSON-like representation of the tag.
        meta: A dictionary of injected runtime metadata (e.g. git_user, current_date).

    Returns:
        The evaluated result, or None if expr is None.

    Raises:
        ExpressionEvaluationError: if the expression is invalid or fails during evaluation.
    """
    if not expr:
        return None

    context = {
        "tag": tag,
        "meta": meta,
    }

    try:
        # compiled = jmespath.compile(expr, custom_functions=CodeTagsCustomFunctions())
        return jmespath.search(expr, context, options=Options(custom_functions=CodeTagsCustomFunctions()))
        # return compiled.search(context)
    except Exception as e:
        print(expr)
        print(context)
        raise ExpressionEvaluationError(f"Error evaluating expression '{expr}': {e}") from e


def initialize_fields_from_schema(
    tag: DataTag, meta: dict, field_infos: dict[str, FieldInfo], is_new: bool = False
) -> dict:
    """
    For a given tag and schema, evaluate all missing or blank fields using their expressions.

    Parameters:
        tag: A JSON representation of the tag (must include data_fields).
        meta: External metadata available to JMESPath.
        field_infos: The schema's field information with FieldInfo entries.

    Returns:
        Updated data_fields dictionary with evaluated defaults applied.
    """
    result_fields = tag["fields"]["data_fields"]

    for field_name, info in field_infos.items():
        expr = ""
        current_value = result_fields.get(field_name)

        if is_new:
            expr = info.get("value_on_new", "")
        elif not current_value:
            expr = info.get("value_on_blank", "")
        else:
            continue  # Field is already populated

        if not expr:
            continue

        value = evaluate_field_expression(expr, tag=tag, meta=meta)
        if value is not None:
            logger.debug(f"Setting {field_name} using jmespath expression {expr}")
            result_fields[field_name] = value

    return result_fields
