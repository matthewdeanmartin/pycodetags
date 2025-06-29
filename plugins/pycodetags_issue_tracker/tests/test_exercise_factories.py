from pycodetags.todo_tag_types_aliases import (
    ALERT,
    BUG,
    CLEVER,
    DOCUMENT,
    FIXME,
    HACK,
    IDEA,
    MAGIC,
    PORT,
    REQUIREMENT,
    STORY,
)


def test_aliases():
    # This needs to be refactored until intellisense works.
    for alias in DOCUMENT, PORT, ALERT, MAGIC, CLEVER, HACK, BUG, FIXME, IDEA, STORY, REQUIREMENT:
        assert alias(comment="Well, it is what it is.")
