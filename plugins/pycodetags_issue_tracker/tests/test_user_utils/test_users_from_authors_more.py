from pycodetags_issue_tracker.user_utils.users_from_authors import parse_authors_file, parse_authors_file_simple


def test_parse_authors_file_idiosyncratic(tmp_path, capsys):
    content = """
# This is the list of authors
Alice <alice@example.com>
Bob
Charlie <charlie@domain.org>  
  David  <david@weird.email>  
Eve <eve@strange-email.com>
Frank (extra note) <frank@note.com>
# A comment line
<unknown@domain.com>
Empty <>
Double Brackets <<double@example.com>>
Malformed Name <malformed@example
Just a name
    """.strip()

    f = tmp_path / "AUTHORS"
    f.write_text(content, encoding="utf-8")

    authors = parse_authors_file(f)

    names = [a["name"] for a in authors]
    # This correct for single column.
    assert "Alice" in names
    assert "Bob" in names
    assert "Charlie" in names
    assert "David" in names
    assert "Eve" in names
    assert "Frank (extra note)" in names
    assert "<unknown@domain.com>" in names  # unmatched, fallback
    assert "Empty <>" in names  # malformed
    assert "Double Brackets <<double@example.com>>" in names
    assert "Malformed Name <malformed@example" in names
    assert "Just a name" in names

    # Confirm some emails were parsed correctly
    emails = {a.get("email") for a in authors if "email" in a}
    assert "alice@example.com" in emails
    assert "david@weird.email" in emails
    assert "frank@note.com" in emails


def test_parse_authors_file_simple_dedupes(tmp_path):
    content = """
Alice <alice@example.com>
Bob <bob@example.com>
Alice <alice@example.com>
Charlie
Bob
    """.strip()

    f = tmp_path / "AUTHORS"
    f.write_text(content, encoding="utf-8")

    names = parse_authors_file_simple(f)

    # Should dedupe names and emails
    assert set(names) >= {"Alice", "Bob", "Charlie", "alice@example.com", "bob@example.com"}
    assert len(names) < 6  # due to deduplication
