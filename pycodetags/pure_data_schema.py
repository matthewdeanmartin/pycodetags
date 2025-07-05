"""
The domain-free schema.

When used, all fields are parsed as custom fields.
"""

from pycodetags.data_tags_schema import DataTagSchema

PureDataSchema: DataTagSchema = {
    "name": "DATA",
    "matching_tags": ["DATA"],
    "default_fields": {
        # No defaults, no domain!
    },
    "data_fields": {
        # No domain fields, pure data!
    },
    "data_field_aliases": {
        # No alias, no domain!
    },
}
