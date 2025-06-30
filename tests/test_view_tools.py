import pytest

from pycodetags.view_tools import group_and_sort


def test_groups_items_by_key_function():
    items = ["apple", "banana", "apricot", "blueberry"]

    def key_fn(x):
        return x[0]

    result = group_and_sort(items, key_fn)
    assert result == {"a": ["apple", "apricot"], "b": ["banana", "blueberry"]}


def test_sorts_items_within_groups():
    items = ["banana", "blueberry", "apple", "apricot"]

    def key_fn(x):
        return x[0]

    result = group_and_sort(items, key_fn)
    assert result == {"a": ["apple", "apricot"], "b": ["banana", "blueberry"]}


def test_handles_empty_list():
    items = []

    def key_fn(x):
        return x[0]

    result = group_and_sort(items, key_fn)
    assert not result


# Null safety problem.
# def test_groups_items_with_unlabeled_key():
#     items = ["apple", None, "banana", ""]
#     key_fn = lambda x: x if x else None
#     result = group_and_sort(items, key_fn)
#     assert result == {"a": ["apple"], "(unlabeled)": [None, "banana", ""]}


def test_raises_error_on_invalid_sort_key():
    items = ["apple", "banana"]

    def key_fn(x):
        return x[0]

    with pytest.raises(ValueError):
        group_and_sort(items, key_fn, sort_key=int)
