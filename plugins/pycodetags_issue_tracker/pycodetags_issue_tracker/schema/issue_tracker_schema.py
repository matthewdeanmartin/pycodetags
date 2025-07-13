from __future__ import annotations

from pycodetags.data_tags.data_tags_schema import DataTagSchema, FieldInfo

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
    "default_fields": {"str": "originator", "date": "origination_date"},
    "data_fields": {
        "priority": "str",  # or str | int?
        "due": "date",
        "tracker": "str",
        "status": "str",
        "category": "str",
        "iteration": "str",  # or str | int?
        "release": "str",  # or str | int | version?
        "assignee": "str",  # or str | list[str]?
        "originator": "str",  # who created the issue
        "origination_date": "date",  # when the issue was created
        "closed_date": "date",  # when the issue was closed
        "change_type": "str",  # e.g. 'Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Security'
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
    "field_infos": {
        "assignee": FieldInfo(
            name="assignee",
            data_type="str",
            valid_values=[],
            label="Assignee",
            description="User who will do the work.",
            aliases=["a"],
            value_on_new="meta.user.name",
            value_on_blank="",
            value_on_delete="",
        ),
        "originator": FieldInfo(
            name="originator",
            data_type="str",
            valid_values=[],
            label="Originator",
            description="User who created the issue.",
            aliases=[],
            value_on_new="meta.user.name",
            value_on_blank="",
            value_on_delete="",
        ),
        "origination_date": FieldInfo(
            name="origination_date",
            data_type="date",
            valid_values=[],
            label="Origination Date",
            description="Date issue created in YYYY-MM-DD format.",
            aliases=[],
            value_on_new="meta.timestamp.date",
            value_on_blank="",
            value_on_delete="",
        ),
        "due": FieldInfo(
            name="due",
            data_type="date",
            valid_values=[],
            label="Due Date",
            description="Date issue will be done in YYYY-MM-DD format.",
            aliases=["d"],
            value_on_new="",
            value_on_blank="",
            value_on_delete="",
        ),
        "release": FieldInfo(
            name="release",
            data_type="str",
            valid_values=[],
            label="Release",
            description="Release completed, will attempt to parse as semantic version A.B.C.",
            aliases=["r"],
            value_on_new="",
            value_on_blank="",
            value_on_delete="meta.project.version",
        ),
        "iteration": FieldInfo(
            name="iteration",
            data_type="str",
            valid_values=[],
            label="Iteration",
            description="User specified meaning, a milestone in a release.",
            aliases=["i"],
            value_on_new="",
            value_on_blank="",
            value_on_delete="",
        ),
        "change_type": FieldInfo(
            name="change_type",
            data_type="str",
            valid_values=["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"],
            label="Change Type",
            description="Field for Keep a Changelog support.",
            aliases=[],
            value_on_new="",
            value_on_blank="'Changed'",
            value_on_delete="",
        ),
        "closed_date": FieldInfo(
            name="closed_date",
            data_type="date",
            valid_values=[],
            label="Closed Date",
            description="Date issue closed in YYYY-MM-DD format.",
            aliases=[],
            value_on_new="",
            value_on_blank="",
            value_on_delete="meta.timestamp.date",
        ),
        "tracker": FieldInfo(
            name="tracker",
            data_type="str",
            valid_values=[],
            label="Tracker",
            description="A URL or Issue as determined by config or URL detection.",
            aliases=["t"],
            value_on_new="",
            value_on_blank="",
            value_on_delete="",
        ),
        "priority": FieldInfo(
            name="priority",
            data_type="str",
            valid_values=[],
            label="Priority",
            description="User specified meaning, urgency of task.",
            aliases=["p"],
            value_on_new="lookup(meta.priority_map, tag.code_tag) || '2'",
            value_on_blank="lookup(meta.priority_map, tag.code_tag) || '2'",
            value_on_delete="lookup(meta.priority_map, tag.code_tag) || '2'",
        ),
        "status": FieldInfo(
            name="status",
            data_type="str",
            valid_values=[],
            label="Status",
            description="Done, plus other user specified values.",
            aliases=["s"],
            value_on_new="planned",
            value_on_blank="",
            value_on_delete="done",
        ),
        "category": FieldInfo(
            name="category",
            data_type="str",
            valid_values=[],
            label="Category",
            description="User specified meaning, any useful categorization of issues.",
            aliases=["c"],
            value_on_new="",
            value_on_blank="",
            value_on_delete="",
        ),
    },
}


def data_fields_as_list(schema: DataTagSchema):
    return list(schema["data_fields"].keys())
