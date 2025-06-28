# tests/test_aggregate.py
import pathlib

import pytest

from pycodetags.aggregate import aggregate_all_kinds, aggregate_all_kinds_multiple_input, merge_collected
from pycodetags.data_tags import DataTag


class DummyTodo:
    pass


@pytest.fixture(autouse=True)
def patch_config_and_plugins(monkeypatch):
    class Config:
        def active_schemas(self):
            return ["todo"]

    monkeypatch.setattr("pycodetags.aggregate.get_code_tags_config", lambda: Config())

    class PM:
        def __init__(self):
            self.hook = self

        def find_source_tags(self, **kwargs):
            return []

    monkeypatch.setattr("pycodetags.aggregate.get_plugin_manager", lambda: PM())

    # Prevent real IO
    monkeypatch.setattr(
        "pycodetags.aggregate.collect_all_todos", lambda module, **kwargs: {"todos": [DummyTodo()], "exceptions": []}
    )

    return monkeypatch


def test_merge_collected_empty():
    assert merge_collected([]) == {"todos": [], "exceptions": []}


def test_merge_collected_multiple():
    a = {"todos": [1, 2], "exceptions": ["e1"]}
    b = {"todos": [3], "exceptions": ["e2", "e3"]}
    merged = merge_collected([a, b])
    assert merged["todos"] == [1, 2, 3]
    assert merged["exceptions"] == ["e1", "e2", "e3"]


def test_aggregate_multiple_inputs(monkeypatch):
    # patch underlying single aggregate
    called = []

    def fake_agg(m, s):
        called.append((m, s))
        return {"todos": [m], "exceptions": [s]}

    monkeypatch.setattr("pycodetags.aggregate.aggregate_all_kinds", fake_agg)

    result = aggregate_all_kinds_multiple_input(["mod1"], ["path1", "path2"])
    # aggregated from module and paths
    assert result["todos"] == ["mod1", "", ""]
    assert result["exceptions"] == ["", "path1", "path2"]


# def test_aggregate_all_kinds_import_module_success(monkeypatch):
#     # create dummy module
#     mod_name = "dummy_mod_for_tests"
#     sys.modules[mod_name] = type(mod_name, (), {})()
#     # create dummy python file for source path
#     p = pytest.temp_dir = pathlib.Path("dummy_file.py")
#     p.write_text("# TODO: test <p:hi>")
#     monkeypatch.setenv if False else None
#     with pytest.raises(TypeError):
#         aggregate_all_kinds("", "nonexistent_folder")  # should raise no files found
#
#     tmp = pathlib.Path(pytest.temp_dir)
#     # should detect .py file and collect pep350 tag
#     monkeypatch.setattr("pycodetags.aggregate.iterate_comments", lambda file, schemas, include_folk_tags: [{"fields":{}, "code_tag":"T", "comment":"c"}])
#     out = aggregate_all_kinds("", str(tmp))
#     assert "todos" in out and isinstance(out["todos"], list)


def test_aggregate_all_kinds_import_error(monkeypatch, capsys):
    # Patch import to raise
    monkeypatch.setattr(
        "pycodetags.aggregate.importlib.import_module", lambda name: (_ for _ in ()).throw(ImportError())
    )
    res = aggregate_all_kinds("nonexistent_module", "")
    captured = capsys.readouterr()
    assert "Could not import module(s)" in captured.err
    assert res["todos"] == []
    assert res["exceptions"] == []


def test_aggregate_all_kinds_with_folk(monkeypatch):
    # simulate plugin producing folk tag (no "fields")
    pkt = DataTag(
        comment="blah",
        code_tag="XYZ",
        fields={"default_fields": {}, "data_fields": {}, "custom_fields": {}, "strict": False},
    )
    monkeypatch.setattr("pycodetags.aggregate.iterate_comments", lambda file, schemas, include_folk_tags: [pkt])

    # plugin find returns list
    def fake_find(**kwargs):
        return [[pkt]]

    PM = type("PM", (), {"hook": type("H", (), {"find_source_tags": staticmethod(fake_find)})})
    monkeypatch.setattr("pycodetags.aggregate.get_plugin_manager", lambda: PM())
    # patch converters to distinguish types
    monkeypatch.setattr("pycodetags.aggregate.convert_pep350_tag_to_TODO", lambda x: "pep")
    monkeypatch.setattr("pycodetags.aggregate.convert_folk_tag_to_TODO", lambda x: "folk")
    tmpdir = pytest.temp_path = pathlib.Path("dummy2.py")
    tmpdir.write_text("# TAG: foo <a:1>", encoding="utf-8")
    res = aggregate_all_kinds("", str(tmpdir))
    # should include folk
    assert "folk" in res["todos"] or "pep" in res["todos"]
