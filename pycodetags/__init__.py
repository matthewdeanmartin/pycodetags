"""Structured code tags: explicit schemas, serialization, and validated source mutations."""

__all__ = [
    # Data tag support
    "DATA",
    "DataTag",
    "DataTagSchema",
    "PureDataSchema",
    "TDGSchema",
    "PEP350Schema",
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
    "TagIndex",
    "apply_mutations",
    "update_tags",
    "delete_tags",
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
from pycodetags.index import TagIndex
from pycodetags.mutator import apply_mutations, delete_tags, update_tags
from pycodetags.plugin_specs import CodeTagsSpec
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.schemas import PEP350Schema, TDGSchema
