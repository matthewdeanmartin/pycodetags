# # tests/test_main_cli.py
#
# import sys
# from unittest import mock
#
# import pytest
#
# import code_tags.__main__ as main_module
#
#
# class DummyException(Exception):
#     pass
#
#
# @pytest.fixture(autouse=True)
# def patch_logging(monkeypatch):
#     dummy = {"dummy": "config"}
#     monkeypatch.setattr(main_module, "generate_config", lambda **kwargs: dummy)
#     monkeypatch.setattr(main_module.logging.config, "dictConfig", lambda cfg: None)
#
#
# @pytest.fixture
# def fake_found():
#     return {"dones": ["a"], "todos": ["b"], "exceptions": ["c"]}
#
#
# def test_no_module_or_src_exits(monkeypatch, capsys):
#     monkeypatch.setattr(sys, "argv", ["prog"])
#     # sys.exit raises SystemExit
#     with pytest.raises(SystemExit) as exc:
#         main_module.main()
#     assert exc.value.code == 1
#     captured = capsys.readouterr()
#     assert "Need to specify an importable module" in captured.out
#
#
# def test_import_error(monkeypatch, capsys):
#     monkeypatch.setattr(sys, "argv", ["prog", "--module", "X"])
#     monkeypatch.setattr(main_module, "aggregate_all_kinds", lambda m1, m2, src: (_ for _ in ()).throw(ImportError))
#     result = main_module.main()
#     captured = capsys.readouterr()
#     assert result == 1
#     assert "Could not import module 'X'" in captured.err
#
#
# def test_empty_data_raises_type_error(monkeypatch):
#     monkeypatch.setattr(sys, "argv", ["prog", "--module", "M", "--src", "S"])
#     monkeypatch.setattr(main_module, "aggregate_all_kinds", lambda *args: {"dones": [], "todos": [], "exceptions": []})
#     with pytest.raises(TypeError):
#         main_module.main()
#
#
# @pytest.mark.parametrize(
#     "flag, func_name",
#     [
#         (["--validate"], "print_validate"),
#         (["--format", "text"], "print_text"),
#         (["--format", "html"], "views_templated.print_html"),
#         (["--format", "json"], "print_json"),
#         (["--format", "keep-a-changelog"], "print_changelog"),
#         (["--format", "todo.md"], "print_todo_md"),
#     ],
# )
# def test_supported_formats_call_correct_function(monkeypatch, fake_found, capsys, flag, func_name):
#     args = ["prog", "--module", "M", "--src", "S"] + flag
#     monkeypatch.setattr(sys, "argv", args)
#     monkeypatch.setattr(main_module, "aggregate_all_kinds", lambda *args: fake_found)
#
#     # Patch all print functions to record calls
#     mock_funcs = {}
#     for fn in ["print_validate", "print_text", "print_json", "print_changelog", "print_todo_md"]:
#         mock_funcs[fn] = mock.Mock()
#         setattr(main_module, fn, mock_funcs[fn])
#     mock_html = mock.Mock()
#     main_module.views_templated.print_html = mock_html
#
#     result = main_module.main()
#     assert result == 0
#
#     if func_name == "views_templated.print_html":
#         mock_html.assert_called_once_with(fake_found)
#     else:
#         mock_funcs[func_name].assert_called_once_with(fake_found)
