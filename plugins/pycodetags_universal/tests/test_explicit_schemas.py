import pytest
from pycodetags_universal.main import javascript_plugin

from pycodetags.app_config.config import CodeTagsConfig


@pytest.mark.parametrize(
    "schema,source",
    [
        ("TDG", "// TODO: title\n// id=17 issue=100\n// body\nconst n = 1;\n"),
        ("PEP350", "// TODO: title\n// body\n// <id=17 issue=100>\n// ordinary\n"),
    ],
)
def test_explicit_javascript_tags_have_canonical_narrative(tmp_path, schema, source):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(f'[tool.pycodetags]\nschema="{schema}"\n', encoding="utf-8")
    path = tmp_path / "source.js"
    path.write_text(source, encoding="utf-8")
    tags = javascript_plugin.find_source_tags(str(path), CodeTagsConfig(str(config_path)))
    assert len(tags) == 1
    assert (tags[0]["title"], tags[0]["body"]) == ("title", "body")
    assert tags[0]["fields"]["data_fields"]["id"] == "17"
    assert tags[0]["original_text"].startswith("// TODO:")
    assert "ordinary" not in tags[0]["original_text"]


def test_strings_and_inline_code_are_not_guessed_as_tags(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text('[tool.pycodetags]\nschema="TDG"\n', encoding="utf-8")
    path = tmp_path / "source.js"
    path.write_text('const s = "// TODO: fake";\n', encoding="utf-8")
    assert javascript_plugin.find_source_tags(str(path), CodeTagsConfig(str(config_path))) == []
