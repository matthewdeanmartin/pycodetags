import logging
from collections.abc import Generator
from pathlib import Path

from pycodetags_issue_tracker.specific_schemas import PEP350Schema

from pycodetags.comment_finder import find_comment_blocks
from pycodetags.data_tags import DataTag, parse_codetags

logger = logging.getLogger(__name__)


def collect_pep350_code_tags(file: str) -> Generator[DataTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        file (str): The path to the file to process.

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    logger.info(f"collect_pep350_code_tags: processing {file}")
    things = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks(Path(file)):
        # Can only be one comment block now!
        thing = parse_codetags(final_comment, PEP350Schema, strict=False)
        things.extend(thing)
    yield from things
