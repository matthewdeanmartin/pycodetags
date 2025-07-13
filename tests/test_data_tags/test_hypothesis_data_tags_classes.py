# # This test code was written by the `hypothesis.extra.ghostwriter` module
# # and is provided under the Creative Commons Zero public domain dedication.
#
# from __future__ import annotations
#
# import typing
#
# from hypothesis import given
# from hypothesis import strategies as st
#
# import pycodetags.data_tags.data_tags_classes
#
#
# @given(
#     code_tag=st.one_of(st.none(), st.text()),
#     comment=st.one_of(st.none(), st.text()),
#     default_fields=st.one_of(st.none(), st.dictionaries(keys=st.text(), values=st.text())),
#     data_fields=st.one_of(st.none(), st.dictionaries(keys=st.text(), values=st.text())),
#     custom_fields=st.one_of(st.none(), st.dictionaries(keys=st.text(), values=st.text())),
#     identity_fields=st.one_of(st.none(), st.lists(st.text())),
#     unprocessed_defaults=st.one_of(st.none(), st.lists(st.text())),
#     file_path=st.one_of(st.none(), st.text()),
#     original_text=st.one_of(st.none(), st.text()),
#     original_schema=st.one_of(st.none(), st.text()),
#     offsets=st.one_of(st.none(), st.tuples(st.integers(), st.integers(), st.integers(), st.integers())),
# )
# def test_fuzz_DATA(
#     code_tag: typing.Union[str, None],
#     comment: typing.Union[str, None],
#     default_fields: typing.Union[dict[str, str], None],
#     data_fields: typing.Union[dict[str, str], None],
#     custom_fields: typing.Union[dict[str, str], None],
#     identity_fields: typing.Union[list[str], None],
#     unprocessed_defaults: typing.Union[list[str], None],
#     file_path: typing.Union[str, None],
#     original_text: typing.Union[str, None],
#     original_schema: typing.Union[str, None],
#     offsets: typing.Union[tuple[int, int, int, int], None],
# ) -> None:
#     pycodetags.data_tags.data_tags_classes.DATA(
#         code_tag=code_tag,
#         comment=comment,
#         default_fields=default_fields,
#         data_fields=data_fields,
#         custom_fields=custom_fields,
#         identity_fields=identity_fields,
#         unprocessed_defaults=unprocessed_defaults,
#         file_path=file_path,
#         original_text=original_text,
#         original_schema=original_schema,
#         offsets=offsets,
#     )
