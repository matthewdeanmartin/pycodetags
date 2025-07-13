# # Tests for extract_comment_blocks function
# def test_extract_comment_blocks_basic(create_dummy_file):
#     content = textwrap.dedent(
#         """
#         # Comment line 1
#         # Comment line 2
#         def func():
#             # Another comment
#             pass
#         """
#     )
#     filename = create_dummy_file("test_comments.py", content)
#     blocks = extract_comment_blocks(filename)
#     assert len(blocks) == 2
#     assert blocks[0] == ["# Comment line 1", "# Comment line 2"]
#     assert blocks[1] == ["# Another comment"]
#
#
# def test_extract_comment_blocks_no_comments(create_dummy_file):
#     content = textwrap.dedent(
#         """
#         def func():
#             pass
#         class MyClass:
#             def method(self):
#                 return 1
#         """
#     )
#     filename = create_dummy_file("test_no_comments.py", content)
#     blocks = extract_comment_blocks(filename)
#     assert len(blocks) == 0
#
#
# def test_extract_comment_blocks_only_comments(create_dummy_file):
#     content = textwrap.dedent(
#         """
#         # Line 1
#         # Line 2
#         # Line 3
#         """
#     )
#     filename = create_dummy_file("test_only_comments.py", content)
#     blocks = extract_comment_blocks(filename)
#     assert len(blocks) == 1
#     assert blocks[0] == ["# Line 1", "# Line 2", "# Line 3"]
#
#
# def test_extract_comment_blocks_separated_by_newline(create_dummy_file):
#     content = textwrap.dedent(
#         """
#         # Comment block 1, line 1
#         # Comment block 1, line 2
#
#         # Comment block 2, line 1
#         """
#     )
#     filename = create_dummy_file("test_separated_by_newline.py", content)
#     blocks = extract_comment_blocks(filename)
#     assert len(blocks) == 2
#     assert blocks[0] == ["# Comment block 1, line 1", "# Comment block 1, line 2"]
#     assert blocks[1] == ["# Comment block 2, line 1"]
#
#
# def test_extract_comment_blocks_with_leading_and_trailing_whitespace(create_dummy_file):
#     content = textwrap.dedent(
#         """
#         #   Comment with leading space
#          # Comment with leading hash and space
#         # Trailing space
#         """
#     )
#     filename = create_dummy_file("test_whitespace_comments.py", content)
#     blocks = extract_comment_blocks(filename)
#     assert len(blocks) == 1
#     assert blocks[0] == [
#         "#   Comment with leading space",
#         "# Comment with leading hash and space",
#         "# Trailing space",
#     ]
