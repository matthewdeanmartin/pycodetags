class PyCodeTagsError(Exception):
    """Base exception for all PyCodeTags errors."""


class DataTagError(PyCodeTagsError):
    """Exception by Data Tag code"""


class ValidationError(PyCodeTagsError):
    """Schema or domain dependent problem with code tag data."""


class SchemaError(PyCodeTagsError):
    """Exception raised on parsing, etc when situations do not conform to a schema"""


class DataTagParseError(PyCodeTagsError):
    """Parse time exceptions"""


class AggregationError(PyCodeTagsError):
    """Exception when combining many code tags into one stream"""


class ModuleImportError(AggregationError):
    """Exceptions when attempting to import and walk the object graph"""


class SourceNotFoundError(AggregationError):
    """File not found during code tag parsing."""


class PluginError(PyCodeTagsError):
    """Exceptions raised during interaction with pluggy plugin system."""


class PluginLoadError(PluginError):
    """Exceptions raised when first interacting with a plugin"""


class PluginHookError(PluginError):
    """Exceptions raised during hook invocation"""


class FileParsingError(PyCodeTagsError):
    """Exceptions raised while parsing code tags."""


class CommentNotFoundError(FileParsingError):
    """No code tag data found in input source."""


class ConfigError(PyCodeTagsError):
    """Exception raised during processing of config file."""


class InvalidActionError(ConfigError):
    """Exception raised during code tag actions."""
