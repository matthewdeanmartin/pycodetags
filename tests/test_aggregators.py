from __future__ import annotations

from pycodetags.aggregate import aggregate_all_kinds


def test_aggregate_all_kinds():
    # TODO: make stronger assertions
    assert aggregate_all_kinds("pycodetags", __file__)
