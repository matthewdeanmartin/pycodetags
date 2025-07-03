class PyCodeTagsError(Exception):
    """Base exception for all PyCodeTags errors."""


class ConfigError(PyCodeTagsError):
    pass


class InvalidActionError(ConfigError):
    pass


class SchemaError(PyCodeTagsError):
    pass


class DataTagParseError(PyCodeTagsError):
    pass


class AggregationError(PyCodeTagsError):
    pass


class ModuleImportError(AggregationError):
    pass


class SourceNotFoundError(AggregationError):
    pass


class PluginError(PyCodeTagsError):
    pass


class PluginLoadError(PluginError):
    pass


class PluginHookError(PluginError):
    pass


class FileParsingError(PyCodeTagsError):
    pass


class CommentNotFoundError(FileParsingError):
    pass


class ValidationError(PyCodeTagsError):
    pass
