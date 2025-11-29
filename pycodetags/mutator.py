"""
This module provides functions for safely mutating source code files
by updating, removing, or inserting pycodetags.
"""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Sequence

# Assuming the DATA class is in a reachable path.
# In a real package, this would be a relative import, e.g., from .data import DATA
from pycodetags.data_tags import DATA
from pycodetags.exceptions import DataTagError


def apply_mutations(
    file_path: str | os.PathLike[str],
    mutations: Sequence[tuple[DATA, DATA | None]],
) -> None:
    """
    Applies multiple updates and/or removals to a single file in one atomic operation.

    This function is the safest way to perform multiple modifications on a file,
    as it reads the file once, applies all changes in memory from end to start
    to avoid offset invalidation, and then writes the result back once.

    Args:
        file_path (Union[str, os.PathLike]): The path to the source file.
        mutations (List[Tuple[DATA, Optional[DATA]]]): A list of tuples,
            where each tuple contains:
            - old_tag (DATA): The tag to be updated or removed. It must have
              been obtained from a previous parse to have accurate offset info.
            - new_tag (Optional[DATA]): The new state of the tag. If None, the
              old_tag will be removed.

    Raises:
        FileNotFoundError: If the specified file_path does not exist.
        DataTagError: If an old_tag cannot be found at its specified offsets,
                      indicating the file was modified externally.
        TypeError: If the input types are incorrect.
    """
    p_file_path = Path(file_path)
    if not p_file_path.is_file():
        raise FileNotFoundError(f"No such file: '{p_file_path}'")

    # --- 1. Read the entire file content ---
    try:
        content = p_file_path.read_text()
    except Exception as e:
        raise OSError(f"Could not read file '{p_file_path}': {e}") from e

    # --- 2. Validate and prepare replacements ---
    replacements = []
    for old_tag, new_tag in mutations:
        if not isinstance(old_tag, DATA) or (new_tag is not None and not isinstance(new_tag, DATA)):
            raise TypeError("mutations must be a list of (DATA, DATA | None) tuples.")

        if not old_tag.offsets or old_tag.original_text is None:
            raise DataTagError(
                "The 'old_tag' must be an object from a parse operation "
                "with valid 'offsets' and 'original_text' attributes."
            )

        # Validation: Check that the text at the stored offsets still matches
        # the original text of the tag. This prevents overwriting a file
        # that has been modified since the tag was parsed.
        start_line, start_char, end_line, end_char = old_tag.offsets

        # This slicing logic is complex and needs to be precise
        lines = content.splitlines(True)
        if start_line == end_line:
            try:
                original_slice = lines[start_line][start_char:end_char]
            except IndexError as ie:
                raise DataTagError("Tag mismatch") from ie
        else:
            # Multi-line tag
            first_line = lines[start_line][start_char:]
            middle_lines = "".join(lines[start_line + 1 : end_line])
            last_line = lines[end_line][:end_char]
            original_slice = first_line + middle_lines + last_line

        # We must be careful with how original_text was stored.
        # Let's normalize whitespace for a more robust comparison.
        if " ".join(original_slice.split()) != " ".join(old_tag.original_text.split()):
            raise DataTagError(
                f"Tag mismatch for '{old_tag.comment}' at {p_file_path}:{start_line + 1}. "
                "The file may have been modified since the tag was parsed."
            )

        replacement_text = new_tag.as_data_comment() if new_tag else ""
        replacements.append((old_tag.offsets, replacement_text))

    # --- 3. Sort by start offset in descending order ---
    # This is the critical step to avoid offset invalidation. By processing
    # from the end of the file backwards, the offsets for earlier parts of
    # the file remain valid for each subsequent replacement.
    replacements.sort(key=lambda item: item[0][0], reverse=True)

    # --- 4. Apply replacements to the content in memory ---
    # This is a bit tricky with multi-line content. A simpler approach
    # might be to work with the raw string content and character offsets.
    # Let's refine the logic to use character offsets from a full string read.
    # This requires a different offset calculation during parsing, but let's
    # assume for now we can derive it. For this implementation, we will
    # stick to line/char offsets and reconstruct carefully.

    lines = content.splitlines(True)  # Keep endings for reconstruction
    for (start_line, start_char, end_line, end_char), new_text in replacements:
        if start_line == end_line:
            # Single-line modification
            line = lines[start_line]
            lines[start_line] = line[:start_char] + new_text + line[end_char:]
        else:
            # Multi-line modification
            # Preserve indentation from the first line for the new text
            indentation = lines[start_line][:start_char]

            # If removing, the new text is empty. If updating, format it.
            formatted_new_text = new_text
            if new_text:
                # Add indentation to all lines of the new text
                new_text_lines = new_text.splitlines(True)
                formatted_new_text = "".join(
                    [f"{indentation}{line.lstrip()}" if index > 0 else line for index, line in enumerate(new_text_lines)]
                )

            # Reconstruct the file around the modification
            first_line_part = lines[start_line][:start_char]
            last_line_part = lines[end_line][end_char:]

            # Combine the parts
            lines[start_line] = first_line_part + formatted_new_text + last_line_part

            # Clear out the lines that were part of the old multi-line tag
            for i in range(start_line + 1, end_line + 1):
                lines[i] = ""

    modified_content = "".join(lines)

    # --- 5. Atomically write the modified content back to the file ---
    try:
        # Write to a temporary file in the same directory, then rename
        temp_file_path = p_file_path.with_suffix(f"{p_file_path.suffix}.tmp")
        temp_file_path.write_text(modified_content)
        os.replace(temp_file_path, p_file_path)
    except Exception as e:
        raise OSError(f"Could not write to file '{p_file_path}': {e}") from e


def delete_tags(
    file_path: str | os.PathLike[str],
    tags_to_delete: list[DATA],
) -> None:
    """
    Syntactic sugar to remove a list of code tags from a file.

    This is a convenience wrapper around apply_mutations.

    Args:
        file_path (Union[str, os.PathLike]): The path to the source file.
        tags_to_delete (List[DATA]): A list of DATA objects to remove.
    """
    mutations = [(tag, None) for tag in tags_to_delete]
    apply_mutations(file_path, mutations)


def replace_with_strings(
    file_path: str | os.PathLike[str],
    replacements: list[tuple[DATA, str]],
) -> None:
    """
    Syntactic sugar to replace a list of code tags with new string content.

    This is a convenience wrapper around apply_mutations. It creates new
    DATA objects from the provided strings. Note that this creates a very
    simple DATA object; only the 'comment' and 'code_tag' fields are set.

    Args:
        file_path (Union[str, os.PathLike]): The path to the source file.
        replacements (List[Tuple[DATA, str]]): A list of tuples, where each is:
            - old_tag (DATA): The tag to be replaced.
            - new_string (str): The raw string for the new comment.
                                This will become the 'comment' of a new DATA tag.
    """
    mutations = []
    for old_tag, new_string in replacements:
        # Create a new DATA object to generate the replacement comment.
        # We carry over the original code_tag.
        new_tag = DATA(code_tag=old_tag.code_tag, comment=new_string)
        mutations.append((old_tag, new_tag))
    apply_mutations(file_path, mutations)


def insert_tags(
    file_path: str | os.PathLike[str],
    insertions: list[tuple[int, DATA, int]],
) -> None:
    """
    Inserts new code tags on specified blank lines in a file.

    Args:
        file_path (Union[str, os.PathLike]): The path to the source file.
        insertions (List[Tuple[int, DATA, int]]): A list of tuples, where each tuple is:
            - line_number (int): The 1-based line number to insert the tag on.
                                 This line MUST be blank (contain only whitespace).
            - tag_to_insert (DATA): The DATA object to insert.
            - indent_level (int): The number of spaces to use for indentation.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a specified line number is invalid or not blank.
        IOError: If the file cannot be read or written.
    """
    p_file_path = Path(file_path)
    if not p_file_path.is_file():
        raise FileNotFoundError(f"No such file: '{p_file_path}'")

    try:
        lines = p_file_path.read_text().splitlines(True)
        # Ensure we can insert after the last line
        if not lines or not lines[-1].endswith(("\n", "\r")):
            lines.append("\n")

    except Exception as e:
        raise OSError(f"Could not read file '{p_file_path}': {e}") from e

    # --- 1. Validate all insertion points before modifying ---
    for line_number, _tag_to_insert, _ in insertions:
        if not (1 <= line_number <= len(lines) + 1):
            raise ValueError(f"Invalid line number: {line_number}. File has {len(lines)} lines.")
        # Check if the target line is blank (only whitespace)
        # Adjust for 0-based index
        if line_number <= len(lines) and lines[line_number - 1].strip():
            raise ValueError(f"Cannot insert tag at line {line_number}. Line is not blank.")

    # --- 2. Sort insertions by line number in descending order ---
    # This ensures that inserting a line doesn't affect the line numbers
    # of subsequent insertions.
    insertions.sort(key=lambda item: item[0], reverse=True)

    # --- 3. Perform the insertions ---
    for line_number, tag_to_insert, indent_level in insertions:
        indentation = " " * indent_level
        tag_text = tag_to_insert.as_data_comment()

        # Indent every line of the generated tag comment
        indented_tag_text = "\n".join(f"{indentation}{line}" for line in tag_text.splitlines()) + "\n"

        # Insert the new text. list.insert is what we need.
        # Use 0-based index.
        lines.insert(line_number - 1, indented_tag_text)

    modified_content = "".join(lines)

    # --- 4. Atomically write the modified content back ---
    try:
        temp_file_path = p_file_path.with_suffix(f"{p_file_path.suffix}.tmp")
        temp_file_path.write_text(modified_content)
        os.replace(temp_file_path, p_file_path)
    except Exception as e:
        raise OSError(f"Could not write to file '{p_file_path}': {e}") from e
