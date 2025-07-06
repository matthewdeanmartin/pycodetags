from pycodetags import PureDataSchema
from pycodetags.__main__ import source_and_modules_searcher

source_and_modules_searcher("validate", [""], [".venv"], PureDataSchema)
