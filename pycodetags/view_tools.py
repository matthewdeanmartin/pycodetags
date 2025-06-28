"""
Like itertools, this is the functional programming code for list[TODO]
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable # noqa[UP035]


def group_and_sort(
    items: list[Any],
    key_fn: Callable[[Any], str],
    sort_items: bool = True,
    sort_key: Callable[[Any], Any] | None = None,
) -> dict[str, list[Any]]:
    """
    Groups and optionally sorts a list of items by a key function.

    Args:
        items: The list of items to group.
        key_fn: A function that returns the grouping key for an item.
        sort_items: Whether to sort the items within each group.
        sort_key: A custom sort key function for sorting items in each group.

    Returns:
        A dictionary mapping keys to lists of items.
        Keys with None or empty values are grouped under '(unlabeled)'.
    """
    grouped: dict[str, list[Any]] = defaultdict(list)

    for item in items:
        raw_key = key_fn(item)
        norm_key = str(raw_key).strip().lower() if raw_key else "(unlabeled)"
        grouped[norm_key].append(item)

    if sort_items:
        for norm_key, group in grouped.items():
            try:
                grouped[norm_key] = sorted(group, key=sort_key or key_fn)
            except Exception as e:
                raise ValueError(f"Failed to sort group '{norm_key}': {e}") from e

    return dict(sorted(grouped.items(), key=lambda x: x[0]))
