"""
Code Tags is a tool and library for working with TODOs into source code.

Only the strongly typed decorators, exceptions and context managers are exported.

Everything else is a plugin.
"""

__all__ = [
    # Data tag support
    "DATA",
    "DataTag",
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
    "CodeTagsConfig",
    # Interactive use
    "inspect_file",
    "list_available_schemas",
]

from pycodetags.app_config import CodeTagsConfig
from pycodetags.common_interfaces import (
    dump,
    dump_all,
    dumps,
    dumps_all,
    inspect_file,
    list_available_schemas,
    load,
    load_all,
    loads,
    loads_all,
)
from pycodetags.data_tags import DATA, DataTag, DataTagSchema
from pycodetags.plugin_specs import CodeTagsSpec
from pycodetags.pure_data_schema import PureDataSchema
