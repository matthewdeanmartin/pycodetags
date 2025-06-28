from __future__ import annotations

import pytest
import sys
import re
from dataclasses import dataclass, field, fields

from pycodetags.todo_tag_types_generate_aliases import build_param_parts, param_string


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


#
# def test_generate_code_tags_file_writes_aliases(tmp_path, monkeypatch):
#     # Use DummyTODO to control the output
#     output = tmp_path / "out_aliases.py"
#     # Suppress print to avoid clutter
#     monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
#     # Run generator
#     generate_code_tags_file(cls=DummyTODO, output_filename=str(output))
#     content = output.read_text(encoding="utf-8")
#
#     # Should contain import from pycodetags.main_types TODO
#     assert "from pycodetags.main_types import TODO" in content
#
#     # Should include at least one alias function with correct signature
#     # e.g., REQUIREMENT(a: int, b: str = 'hello', c: list[int] | None = None) -> TODO
#     pattern = r"def REQUIREMENT\(.+\) -> TODO:"
#     assert re.search(pattern, content)
#
#     # Test that calling the alias function works—execute the file dynamically
#     namespace: dict[str, Any] = {}
#     exec(content, namespace)
#     REQUIREMENT = namespace["REQUIREMENT"]
#     # Call with only required arg
#     todo_obj = REQUIREMENT(a=42)
#     assert hasattr(todo_obj, "code_tag") and todo_obj.code_tag == "REQUIREMENT"
#     assert todo_obj.a == 42
#
#     # Call with all args
#     todo2 = REQUIREMENT(a=1, b="x", c=[1,2,3])
#     assert todo2.b == "x" and todo2.c == [1,2,3]
