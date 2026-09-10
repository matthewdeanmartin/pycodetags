"""Transcoding preserves the shared record contract rather than historical formatting."""

import pytest

from pycodetags import dumps, loads


@pytest.mark.parametrize("start, finish", [("TDG", "PEP350"), ("PEP350", "TDG")])
def test_transcoding_preserves_identity_and_body(start, finish):
    source = (
        "# TODO: title\n# body\n#\n# more body\n# <id=17 issue=100 tracker=https://github.com/acme/repo/issues/101>"
    )
    original = loads(source, schema="PEP350")
    intermediate = loads(dumps(original, schema=start), schema=start)
    final = loads(dumps(intermediate, schema=finish), schema=finish)
    assert final.to_flat_dict(include_comment_and_tag=True) == original.to_flat_dict(include_comment_and_tag=True)
    assert final.tag_id == "17"
    assert final.body == "body\n\nmore body"


def test_editing_body_does_not_write_stale_dictionary_values():
    tag = loads("# TODO: title\n# old body", schema="TDG")
    tag.body = "new body"
    assert loads(dumps(tag), schema="TDG").body == "new body"
