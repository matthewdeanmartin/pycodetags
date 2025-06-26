"""
Tasks that the maintainers of code_tags need to do.
"""

from __future__ import annotations

from pycodetags.todo_tag_types import TODO

TODOs = [
    TODO(assignee="Matth", comment="Verify if TODOs can safely exist inside the code_tag library.", release_due="0.5.0")
]
