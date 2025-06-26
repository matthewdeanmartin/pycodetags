"""
Segregated TODO comments.
"""

# TODO: Implement "DONE" File Generation:
# This needs to be fully implemented to generate a file that tracks completed TODOs,
# addressing the identified problem of comment identity. A clear mechanism for
# associating a "DONE" entry with its original "TODO" is crucial, possibly by
# including unique identifiers in the TODOs themselves.
# <assignee:matth release:0.2.0 file:views.py>

# TODO: Enhanced Multiline Comment Parsing:
# While `folk_code_tags.py` has `allow_multiline`, its implementation might need
# refinement to robustly handle complex multiline comments across different styles.
# <assignee:matth release:0.2.0 file:folk_code_tags.py>

# BUG: Address `_runtime_exceptions` issue:
# The comment in `collect_all_todos` states `_runtime_exceptions` is never really used.
# This should be addressed either by removing it or integrating its use.
# <assignee:matth release:0.2.0 file:collect.py>

# TODO: Refactor `_collect_recursive`:
# The `_collect_recursive` method in `TodoCollector` seems to have some potentially
# overlapping logic, specifically around handling classes and functions/methods.
# Review and refactor to ensure clear responsibilities and avoid redundant checks.
# <assignee:matth release:0.2.0 file:collect.py>
