# File: tests/test_users_from_authors.py

from pycodetags_issue_tracker.users_from_authors import parse_authors_file


def test_parse_authors_file(tmp_path):
    # Create a dummy AUTHORS file for testing
    dummy_authors_content = """
# Project Contributors

John Doe <john.doe@example.com>
Jane Smith
Alice Wonderland <alice@wonderland.org>
Bob The Builder (Maintenance Lead)
    # A comment line
Charlie Chaplin
    """
    authors_file = tmp_path / "AUTHORS_test.txt"
    authors_file.write_text(dummy_authors_content.strip(), encoding="utf-8")

    # Call the function
    parsed_authors = parse_authors_file(str(authors_file))

    # Expected result
    expected_authors = [
        {"name": "John Doe", "email": "john.doe@example.com"},
        {"name": "Jane Smith"},
        {"name": "Alice Wonderland", "email": "alice@wonderland.org"},
        {"name": "Bob The Builder (Maintenance Lead)"},
        {"name": "Charlie Chaplin"},
    ]

    # Assertions
    assert parsed_authors == expected_authors

    # Clean up is handled by pytest's tmp_path
