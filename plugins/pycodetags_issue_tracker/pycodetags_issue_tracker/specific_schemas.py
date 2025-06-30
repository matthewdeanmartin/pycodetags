from pycodetags.data_tags import DataTagSchema

PEP350Schema: DataTagSchema = {
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
