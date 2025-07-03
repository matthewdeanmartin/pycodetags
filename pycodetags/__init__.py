"""
Code Tags is a tool and library for working with TODOs into source code.

Only the strongly typed decorators, exceptions and context managers are exported.

Everything else is a plugin.
"""

__all__ = [
    # Data tag support
    "DATA",
    "DataTagSchema",
    "PureDataSchema",
    # Serialization interfaces
    "dumps",
    "dump",
    "dump_all",
    "dumps_all",
    # Deserialization interfaces
    "loads",
    "load",
    "load_all",
    "loads_all",
    # Plugin interfaces
    "CodeTagsSpec",
]

from pycodetags.common_interfaces import dump, dump_all, dumps, dumps_all, load, load_all, loads, loads_all
from pycodetags.data_schema import PureDataSchema
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTagSchema
from pycodetags.plugin_specs import CodeTagsSpec
