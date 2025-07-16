# PYCODETAGS PEP: Adding Update Functionality to PyCodeTags

| PEP:             | 007                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Adding Update Functionality to PyCodeTags                                         |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | Gemini 2.5 Flash (a large language model by Google)                               |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-15                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.7.0                                                                           |


## **Abstract**

This PEP proposes the addition of functionality to the pycodetags library that allows for the modification and removal of existing code tags within source files. Currently, pycodetags can parse and extract code tags, but it lacks the ability to write changes back to the original files. This proposal addresses common use cases such as marking tasks as complete, re-assigning responsibilities, re-formatting tags, and removing outdated comments. It also explicitly addresses critical safety concerns related to file modification, particularly the challenges posed by offset invalidation and the reliability of comment detection.


## **Motivation**

The pycodetags library provides a powerful mechanism for treating code comments as structured data. However, its utility is limited by its current read-only nature. To fully integrate pycodetags into development workflows and enable more dynamic use cases, the ability to update and remove tags in source files is essential.

Key motivations include:



* **Comment Removal:** When a TODO, FIXME, or BUG tag is addressed, developers need a programmatic way to remove it from the source code. Manual removal is error-prone and doesn't fit into automated pipelines.
* **Re-formatting and Standardization:** As codebases evolve, the style or required fields for code tags might change. An update mechanism would allow for automated re-formatting of existing tags to adhere to new standards or correct inconsistencies (e.g., fixing typos in field names, adjusting whitespace).
* **Filling in Fields and Status Updates:** Code tags often represent tasks or issues. The ability to update fields within a tag (e.g., assignee, priority, status, date_completed) is crucial. For instance, a TODO tag could be updated to status:done or assignee:new_developer.
* **Integration with External Systems:** Plugins that integrate pycodetags with issue trackers (e.g., Jira, GitHub Issues) would greatly benefit from being able to update the source code tag when the corresponding issue's status changes externally. This enables a two-way synchronization.
* **Automated Code Maintenance:** Tools built on pycodetags could automatically clean up or modify tags as part of continuous integration or nightly builds, ensuring code comments remain relevant and actionable.

Without update functionality, pycodetags remains primarily a reporting tool. Adding this capability transforms it into a more comprehensive code intelligence and maintenance solution.


## **Rationale**

The primary design principle for implementing update functionality is **safety and reliability**. Modifying source code files programmatically carries inherent risks, especially concerning data corruption. Therefore, the proposed approach prioritizes robust handling of file content and offsets.

The core strategy for updating will involve:



1. **Full File Read:** The entire content of the target file will be read into memory.
2. **Comprehensive Parsing:** All existing DATA tags within the file will be re-parsed using the library's existing parsing mechanisms, ensuring that their exact offsets (start line, start character, end line, end character) and original_text are captured.
3. **Targeted Replacement:** The specific old_tag to be updated (identified by its file_path, offsets, and original_text) will be located. Its original_text will be replaced with the new_tag's generated string representation. For removal, the old_tag's text will be replaced with an empty string or appropriate whitespace.
4. **File Reconstruction:** The file content will be reconstructed by taking the parts of the original file before the old_tag, inserting the new_tag's content, and then appending the parts after the old_tag. This avoids complex in-place byte manipulation.
5. **Atomic Write:** The modified content will be written back to the original file, ideally using a safe write pattern (e.g., writing to a temporary file and then atomically replacing the original).

This approach addresses the offset invalidation problem by effectively re-calculating all offsets for the entire file during the reconstruction phase. By requiring the old_tag object (obtained from a prior inspect_file or load_all call), we ensure that the update operation is based on accurate, previously parsed information, including the exact original_text and offsets. This allows for a crucial pre-check: verifying that the original_text at the given offsets in the current file still matches the old_tag's original_text before proceeding with modification, thereby detecting external changes to the file.


## **Specification**

This PEP proposes adding new public functions to the pycodetags.common_interfaces module:


### **pycodetags.update(file_path: Union[str, os.PathLike, Path], old_tag: DATA, new_tag: DATA) -> None**

Updates a single DATA tag in the specified file_path.



* file_path: The path to the source file containing the tag. This can be a string, an os.PathLike object, or a pathlib.Path object.
* old_tag: An instance of DATA representing the tag to be updated. This DATA object **must** have been obtained from a prior pycodetags.inspect_file or pycodetags.load_all call, ensuring that its file_path, offsets, and original_text attributes are populated and accurate relative to the file it was parsed from.
* new_tag: An instance of DATA representing the desired state of the tag after the update. Its as_data_comment() method will be used to generate the new text.

**Behavior:**



1. Reads the content of file_path.
2. Performs a validation: It checks if the old_tag.file_path matches file_path and if the old_tag.offsets and old_tag.original_text precisely match the content found at those offsets in the current file_path. If not, a DataTagError is raised (e.g., "Mismatched tag or file modified externally").
3. Generates the string representation of new_tag using new_tag.as_data_comment().
4. Reconstructs the file content by replacing the old_tag.original_text at its offsets with the new string.
5. Writes the updated content back to file_path.


### **pycodetags.remove(file_path: Union[str, os.PathLike, Path], tag_to_remove: DATA) -> None**

Removes a single DATA tag from the specified file_path.



* file_path: The path to the source file containing the tag. This can be a string, an os.PathLike object, or a pathlib.Path object.
* tag_to_remove: An instance of DATA representing the tag to be removed. Similar to update, this object **must** have been obtained from a prior pycodetags.inspect_file or pycodetags.load_all call, with accurate file_path, offsets, and original_text.

**Behavior:**



1. Reads the content of file_path.
2. Performs a validation similar to update to ensure the tag_to_remove is accurately identified.
3. Reconstructs the file content by replacing the tag_to_remove.original_text at its offsets with an empty string, effectively deleting the comment block.
4. Writes the updated content back to file_path.


### **pycodetags.update_all(file_path: Union[str, os.PathLike, Path], updates: list[tuple[DATA, DATA | None]]) -> None**

Applies multiple updates and/or removals to a single file in one operation. This is the most efficient and safest way to perform multiple modifications on a file, as it minimizes file I/O and handles offset shifts internally.



* file_path: The path to the source file. This can be a string, an os.PathLike object, or a pathlib.Path object.
* updates: A list of tuples, where each tuple is (old_tag, new_tag).
    * old_tag: The DATA object to be updated/removed (must be from a prior inspect_file or load_all).
    * new_tag: The DATA object representing the new state, or None if the old_tag should be removed.

**Behavior:**



1. Reads the content of file_path.
2. For each (old_tag, new_tag) pair in updates:
    * Validates old_tag against the current file content and its offsets.
    * Determines the replacement_text (either new_tag.as_data_comment() or "" if new_tag is None).
3. Sorts the updates by old_tag.offsets in descending order. This is critical to ensure that changes to earlier parts of the file do not invalidate offsets for later changes within the same operation. By processing from the end of the file backward, relative offsets remain valid for each subsequent replacement.
4. Iteratively applies the replacements to the file content in memory.
5. Writes the final modified content back to file_path.

**Error Handling:**



* FileNotFoundError: If file_path does not exist.
* DataTagError: If old_tag (or tag_to_remove) cannot be precisely located in the file (e.g., original_text or offsets mismatch, indicating external modification or an invalid DATA object).
* TypeError: If old_tag or new_tag are not DATA instances or if new_tag is not None for removal.


## **Backwards Compatibility**

The proposed additions are new functions to the public API. They do not alter the behavior of existing functions like inspect_file, load, loads, dump, or dumps. Therefore, this PEP is fully backward-compatible with existing pycodetags usage.


## **Safety Issues and Challenges Addressed**

File modification is a sensitive operation. This proposal specifically addresses the following challenges:



1. **Offset Invalidation with Multiple Tags:**
    * **Problem:** When a comment's length changes (either by updating its text or removing it), the absolute line and character offsets of all subsequent comments in the same file are shifted. A naive approach that modifies the file in-place for each tag would quickly lead to incorrect modifications or file corruption.
    * **Solution:** The update_all function is introduced to handle multiple changes in a single, safe pass. By reading the entire file, applying all changes to an in-memory representation, and then writing the complete modified content back, the issue of cascading offset invalidation is mitigated. Specifically, sorting updates by offset in *descending* order (from end of file to beginning) for update_all ensures that each replacement happens relative to an unchanging part of the file, or a part that has already been processed without affecting the offsets of remaining targets.
    * **User Responsibility:** Users are expected to obtain the DATA objects for old_tag or tag_to_remove directly from pycodetags.inspect_file or pycodetags.load_all. These objects carry the necessary file_path, offsets, and original_text attributes, which are used for robust identification and validation before modification.
2. **Reliability of Comment Detection and Offsets (especially with ast_comments fallback):**
    * **Problem:** The accuracy of comment offsets is crucial. While ast_comments provides robust AST-based comment parsing and accurate offsets, the fallback find_comment_blocks_from_string_fallback (which uses regex and line-by-line scanning) might be less precise, especially for complex multi-line comments or comments closely intertwined with code. If offsets are incorrect, the update operation could replace the wrong part of the file.
    * **Mitigation:**
        * **Validation:** The proposed update and remove functions include a critical validation step: they verify that the original_text stored in the DATA object matches the actual text found at the offsets in the current file. If there's a mismatch, it indicates either an incorrect DATA object (e.g., from an outdated parse) or that the file has been modified externally since the DATA object was created. In such cases, a DataTagError is raised, preventing accidental corruption.
        * **Recommendation:** Users are strongly encouraged to install ast_comments for the most reliable comment parsing and offset detection. The library will log warnings if ast_comments is not available and the fallback is used, advising users of potential limitations.
        * **Atomic Operations:** The atomic write pattern (write to temp, then rename) helps ensure that if an error occurs during the write, the original file is not left in a corrupted state.
3. **External File Modifications:**
    * **Problem:** A file might be modified by another process or editor between the time pycodetags reads a tag and when it attempts to write an update.
    * **Mitigation:** The validation step mentioned above (checking original_text against current file content at offsets) serves as a basic concurrency check. While not a full locking mechanism, it prevents pycodetags from blindly overwriting content that has changed unexpectedly. Users of pycodetags in highly concurrent environments should implement their own file locking or version control integration.


## **Copyright**

This document is placed under the MIT license.
