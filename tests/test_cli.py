#
#
# from pycodetags import __main__ as cli
#
# Bad mocking, it leaves the mock for other tests.
# def test_internal_views_all_formats(): #capsys):
#     tv = cli.InternalViews()
#     fake_data = object()
#     # test each format routes to correct print_x function
#     formats = {
#         "text": "print_text",
#         "html": "print_html",
#         "json": "print_json",
#         "keep-a-changelog": "print_changelog",
#         "todo.md": "print_todo_md",
#         "done": "print_done_file",
#     }
#     for fmt, fnname in formats.items():
#         called = {}
#         setattr(cli, fnname, lambda data, c=called: c.setdefault("ok", True))
#         assert tv.code_tags_print_report(fmt, fake_data)
#         assert called.get("ok") is True
#
#     # unknown format
#     assert tv.code_tags_print_report("nonsense", fake_data) is False
