# Issue Tracker Plugin

Issue tracker items are actionable items with at least a work flow of to-do and done.

```python
# TODO: Improve chase logic to avoid obstacles (plants). 
#  <Bob due=09/01/2025 release_due=2.0.0 category="Chase Algorithm" 
#       status=Development iteration=3 tracker="https://example.com/FSH-8">
```

## Schema

Follows much of PEP350.

```python
from pycodetags.data_tags import DataTagSchema

IssueTrackerSchema: DataTagSchema = {
    "name": "TODO",
    "matching_tags": [
        "TODO",
        "REQUIREMENT",
        "STORY",
        "IDEA",
        # Defects
        "FIXME",
        "BUG",
        # Negative sentiment
        "HACK",
        "CLEVER",
        "MAGIC",
        "ALERT",
        # Categories of tasks
        "PORT",
        "DOCUMENT",
    ],
    "default_fields": {"str": "assignee", "date": "origination_date"},
    "data_fields": {
        "priority": "str",  # or str | int?
        "due": "date",
        "tracker": "str",
        "status": "str",
        "category": "str",
        "iteration": "str",  # or str | int?
        "release": "str",  # or str | int?
        "assignee": "str",  # or str | list[str]?
        "originator": "str",
    },
    "data_field_aliases": {
        "p": "priority",
        "d": "due",
        "t": "tracker",
        "s": "status",
        "c": "category",
        "i": "iteration",
        "r": "release",
        "a": "assignee",
    },
}
```

## Complete Example

See /demo/ folder for a hypothetical application with lots of code tags.

```python
import random
from pycodetags_issue_tracker import TODO, DOCUMENT, FIXME

@TODO(
    assignee="Carl",
    due="10/01/2025",
    release_due="2.0.0",
    category="Plant Generator",
    status="Planning",
    comment="Enhance Plant class to support different types and interactions.",
)
class Plant:
    def __init__(self, x: int, y: int, char: str):
        self.x = x
        self.y = y
        self.char = char
        # TODO: Implement plant growth over time. <Carl>

    @DOCUMENT(
        originator="Kstar",
        comment="Add detailed documentation for Plant.update and explain why NotImplementedError is raised.",
    )
    def update(self):
        """
        Updates the plant's state (e.g., growth animation).
        """
        # NOT IMPLEMENTED: Plant animation logic for swaying or growing.
        raise NotImplementedError(
            "Plant animation is not yet implemented. This feature will add dynamic plant swaying."
        )


@TODO(
    assignee="Kstar",
    due="08/15/2025",
    release_due="1.5.0",
    category="Wave Generator",
    status="Development",
    comment="Make wave generation more realistic and less static.",
)
class Wave:
    # DONE: Static wave character setup completed. <Bob due=05/01/2024 release=1.0.0 category=Wave Generator>
    def __init__(self, width: int, char_set: list[str]):
        self.width = width
        self.char_set = char_set
        self.wave_pattern_index = 0
        self.wave_pattern = ""
        self._generate_pattern()

    @TODO(
        originator="Bob",
        comment="Refine wave pattern generation for more organic look.",
        category="Wave Generator",
        status="Planning",
        iteration="2",
    )
    def _generate_pattern(self):
        """Generates a random wave pattern."""
        self.wave_pattern = "".join(random.choice(self.char_set) for _ in range(self.width))

    @FIXME(
        assignee="Carl",
        tracker="https://example.com/FSH-4",
        comment="Wave animation is choppy, needs smoother transitions.",
    )
    @TODO(
        assignee="Kstar",
        tracker="https://example.com/FSH-3",
        comment="Make wave pattern more dynamic and fluid (e.g., gentle oscillation).",
    )
    def update(self):
        """
        Updates the wave pattern for animation.
        """
        # TODO: Make wave pattern more dynamic and fluid (e.g., gentle oscillation). <Kstar tracker=https://example.com/FSH-3>
        # FIXME: Wave animation is choppy, needs smoother transitions. <Carl tracker=https://example.com/FSH-4>
        
        # Simple scrolling wave animation
        self.wave_pattern_index = (self.wave_pattern_index + 1) % len(self.wave_pattern)
        self.wave_pattern = self.wave_pattern[1:] + self.wave_pattern[0]
```

## Actions

Raise error in build script when due.

## Second Order Plugins

These are not complete

- Issue Tracker Sync



## Configuration

No workflow or schema is one-size-fits all, so you will almost certainly want to do some configuration.

The expectation is that this config is used at development time, optionally on the build server and *not* when
deployed to production or an end users machine. If you are using only comment code tags, it is not an issue. There
is a runtime cost or risk only when using strongly typed code tags.

```toml
[tool.code_tags]
# Range Validation, Range Sources
# Empty list means use file
valid_authors = []
valid_authors_file = "AUTHORS.md"
# Can be Gnits, single_column, humans.txt
valid_authors_schema = "single_column"
# Case-insensitive. Needs at least "done"
valid_status = [
    "planning",
    "ready",
    "done",
    "development",
    "inprogress",
    "testing",
    "closed",
    "fixed",
    "nobug",
    "wontfix"
]
# Only displayed
valid_categories = []
# Only displayed
valid_priorities = ["high", "medium", "low"]

# Used to support change log generation and other features.
closed_status = ["done", "closed", "fixed", "nobug", "wontfix"]
# Empty list means no restrictions
valid_releases = []
# Use to look up valid releases (versions numbers)
valid_releases_file = "CHANGELOG.md"
valid_releases_file_schema = "CHANGELOG.md"
# Used in sorting and views
releases_schema = "semantic"
# Subsection of release. Only displayed.
valid_iterations = ["1", "2", "3", "4"]

# Empty list means all are allowed
valid_custom_field_names = []
# Originator and origination date are important for issue identification
# Without it, heuristics are more likely to fail to match issues to their counterpart in git history
mandatory_fields = ["originator", "origination_date"]
# Helpful for parsing tracker field, used to make ticket a clickable url
tracker_domain = "example.com"
# Can be url or ticket
tracker_style = "url"

# Active user from "os", "env", "git"
user_identification_technique = "os"
# .env variable if method is "env"
user_env_var = "CODE_TAGS_USER"

# Defines the action for a TODO condition: "stop", "warn", "nothing".
enable_actions = true
default_action = "warn"
action_on_past_due = true
action_only_on_responsible_user = true

# Environment detection
disable_on_ci = true

# Use .env file
use_dot_env = true

# default CLI arguments
modules = ["demo","code_tags"]
src = ["demo", "code_tags", "tests", "plugins"]
active_schemas = ["todo", "folk"]
```
