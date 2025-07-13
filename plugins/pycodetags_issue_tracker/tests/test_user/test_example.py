import os

from pycodetags_issue_tracker.user_utils.users_from_authors import parse_authors_file


def test_example() -> None:
    """
    Example function to demonstrate how to use the parse_authors_file function.
    """
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
    with open("AUTHORS_test.txt", "w", encoding="utf-8") as f:
        f.write(dummy_authors_content.strip())

    parsed_authors = parse_authors_file("AUTHORS_test.txt")

    print("Parsed Authors:")
    for author in parsed_authors:
        print(author)

    os.remove("AUTHORS_test.txt")
