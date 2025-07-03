"""
Parse specific schemas of data tags
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from pycodetags import folk_code_tags
from pycodetags.comment_finder import find_comment_blocks_from_string
from pycodetags.data_tags import DataTag, DataTagSchema, parse_codetags
from pycodetags.exceptions import SchemaError
from pycodetags.folk_code_tags import FolkTag

logger = logging.getLogger(__name__)


def iterate_comments_from_file(
    file: str, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        file (str): The path to the file to process.
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    logger.info(f"iterate_comments: processing {file}")
    yield from iterate_comments(Path(file).read_text(encoding="utf-8"), Path(file), schemas, include_folk_tags)


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        source (str): The source text to process.
        source_file (Path): Where did the source come from
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    if not schemas and not include_folk_tags:
        raise SchemaError("No active schemas, not looking for folk tags. Won't find anything.")
    things: list[DataTag | FolkTag] = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks_from_string(source):
        # Can only be one comment block now!
        logger.debug(f"Search for {[_['name'] for _ in schemas]} schema tags")
        found_data_tags = []
        for schema in schemas:
            found_data_tags = parse_codetags(final_comment, schema, strict=False)
            if found_data_tags:
                logger.debug(f"Found data tags! : {','.join(_['code_tag'] for _ in found_data_tags)}")
            things.extend(found_data_tags)

        if not found_data_tags and include_folk_tags:
            # BUG: fails if there are two in th same.
            # TODO: blank out consumed text, reconsume bock
            found_folk_tags: list[FolkTag] = []
            # TODO: support config of folk schema.
            folk_code_tags.process_text(
                final_comment,
                allow_multiline=True,
                default_field_meaning="assignee",
                found_tags=found_folk_tags,
                file_path=str(source_file) if source_file else "",
                valid_tags=[],
            )
            if found_folk_tags:
                logger.debug(f"Found folk tags! : {','.join(_['code_tag'] for _ in found_folk_tags)}")
            things.extend(found_folk_tags)

    yield from things
