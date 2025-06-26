import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pycodetags import TODO, TodoException
from pycodetags.collection_types import CollectedTODOs
from pycodetags.views_templated import print_html


@pytest.fixture
def fake_collected_todos() -> CollectedTODOs:

    return {
        "todos": [TODO(comment="todo"), TODO(status="done", closed_date="1950-1-1")],
        "exceptions": [TodoException(message="oops")],
    }


@patch("pycodetags.views_templated.pkg_resources.files")
@patch("pycodetags.views_templated.jinja2.Template")
@patch("pycodetags.views_templated.webbrowser.open")
def test_print_html_renders_and_writes(mock_browser, mock_template_class, mock_files, tmp_path, fake_collected_todos):
    mock_template_instance = MagicMock()
    mock_template_instance.render.return_value = "<html>OK</html>"
    mock_template_class.return_value = mock_template_instance

    mock_open_file = mock_open(read_data="template text")
    fake_file = MagicMock()
    fake_file.open = mock_open_file
    mock_files.return_value.joinpath.return_value = fake_file

    output = tmp_path / "site"
    print_html(fake_collected_todos, output)

    mock_template_instance.render.assert_called_once()
    assert (output / "index.html").read_text(encoding="utf-8") == "<html>OK</html>"
    if not any(key in os.environ for key in ("CI", "GITHUB_ACTIONS")):
        mock_browser.assert_called_once()


@patch("pycodetags.views_templated.pkg_resources.files")
@patch("pycodetags.views_templated.jinja2.Template")
@patch("pycodetags.views_templated.webbrowser.open")
def test_print_html_skips_browser_in_ci(mock_browser, mock_template_class, mock_files, tmp_path, fake_collected_todos):
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>CI</html>"
    mock_template_class.return_value = mock_template

    mock_open_file = mock_open(read_data="template")
    mock_files.return_value.joinpath.return_value.open = mock_open_file

    output = tmp_path / "site"

    with patch.dict(os.environ, {"CI": "1"}):
        print_html(fake_collected_todos, output)

    mock_browser.assert_not_called()
    assert (output / "index.html").read_text(encoding="utf-8") == "<html>CI</html>"


@patch("pycodetags.views_templated.pkg_resources.files")
@patch("pycodetags.views_templated.jinja2.Template")
def test_print_html_raises_on_empty(mock_template_class, mock_files, tmp_path):
    mock_template = MagicMock()
    mock_template.render.return_value = "should not render"
    mock_template_class.return_value = mock_template

    mock_open_file = mock_open(read_data="template")
    mock_files.return_value.joinpath.return_value.open = mock_open_file

    empty_data = {"todos": [], "dones": [], "exceptions": []}
    with pytest.raises(TypeError, match="No data to render"):
        print_html(empty_data, tmp_path)
