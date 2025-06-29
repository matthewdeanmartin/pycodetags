from pycodetags.data_tags import DataTagSchema

PEP350Schema: DataTagSchema = {
    "matching_tags": [
        "TODO",
        "FIXME",
        "BUG",
        "HACK",
        "CLEVER",
        "MAGIC",
    ],
    "default_fields": {"str": "assignee", "date": "origination_date"},
    "data_fields": {
        "priority": "priority",
        "due": "due",
        "tracker": "tracker",
        "status": "status",
        "category": "category",
        "iteration": "iteration",
        "release": "release",
        "assignee": "assignee",
        "originator": "originator",
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
