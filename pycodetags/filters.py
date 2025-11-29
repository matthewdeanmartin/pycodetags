import logging
from collections.abc import Callable
from typing import Any

import jmespath

from pycodetags.data_tags.data_tags_classes import DATA

logger = logging.getLogger(__name__)


class InvalidJMESPathFilter(Exception):
    pass


def compile_jmes_filter(expression: str) -> Callable[[dict[str, Any]], bool]:
    try:
        compiled = jmespath.compile(expression)
    except jmespath.exceptions.JMESPathError as e:
        raise InvalidJMESPathFilter(f"Invalid JMESPath expression: {e}") from e

    def predicate(flat_dict: dict[str, Any]) -> bool:
        try:
            result = compiled.search(flat_dict)
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to evaluate JMESPath expression: {e}")
            return False

    return predicate


def filter_data_by_expression(data_list: list[DATA], expression: str) -> list[DATA]:
    # print([
    #     item.to_flat_dict(include_comment_and_tag=True) for item in data_list
    # ])
    pred = compile_jmes_filter(expression)
    return [item for item in data_list if pred(item.to_flat_dict(include_comment_and_tag=True))]
