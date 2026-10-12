"""Structured code tags: explicit schemas, serialization, and validated source mutations."""

__all__ = [
    # Data tag support
    "DATA",
    "CodeTagsConfig",
    # Plugin interfaces
    "CodeTagsSpec",
    "DataTag",
    "DataTagSchema",
    "PEP350Schema",
    "PureDataSchema",
    "TDGSchema",
    "TagIndex",
    "apply_mutations",
    "delete_tags",
    "dump",
    "dump_all",
    # Serialization interfaces
    "dumps",
    "dumps_all",
    # Interactive use
    "inspect_file",
    "list_available_schemas",
    "load",
    "load_all",
    # Deserialization interfaces
    "loads",
    "loads_all",
    "update_tags",
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
from pycodetags.index import TagIndex
from pycodetags.mutator import apply_mutations, delete_tags, update_tags
from pycodetags.plugin_specs import CodeTagsSpec
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.schemas import PEP350Schema, TDGSchema
