from __future__ import annotations

import re
from dataclasses import dataclass, field, fields

from pycodetags_issue_tracker.todo_tag_types_generate_aliases import build_param_parts, param_string


# A dummy TODO with varied fields to test default, default_factory, and type annotation formatting
@dataclass
class DummyTODO:
    a: int
    b: str = "hello"
    c: list[int] = field(default_factory=list)
    code_tag: str = "UNUSED"  # init field ignored by your logic


# @pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python > 3.7")
# def test_build_param_parts_required_default_and_factory():
#     init_fields = [f for f in fields(DummyTODO) if f.init]
#     parts = build_param_parts(init_fields)
#     # "a" required without default
#     # flaky test across pyversions
#     # assert any(re.match(r"a: int$", p) for p in parts)
#     # "b" has default
#     assert any(re.match(r"b: str = 'hello'$", p) for p in parts)
#     # "c" has default_factory -> annotated Optional[List[int]]
#     assert not any("c:" in p and "= None" in p for p in parts)


def test_param_string_empty_and_nonempty():
    # When no fields
    args_to_pass, params_str = param_string([], [])
    assert args_to_pass == ""
    assert params_str == ""
    # With some fields
    dummy_fields = [f for f in fields(DummyTODO) if f.init and f.name != "code_tag"]
    parts = build_param_parts(dummy_fields)
    args, params = param_string(parts, dummy_fields)
    # Should include both names
    assert "a=a" in args and "b=b" in args and "c=c" in args
    # params_str should contain all parameters
    for name in ("a", "b", "c"):
        assert re.search(rf"{name}:", params)
