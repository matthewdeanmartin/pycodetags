# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-07-13
### Changed
- Reorganize tests into subdirectories by category (test_config, test_schema)
- Clean up schema field signature trailing whitespace in issue tracker alias functions
### Fixed
- Fix data quality issues in code tag parsing and field population
- Update pyproject.toml dependency declarations for plugin compatibility

## [0.2.0] - 2025-07-07
### Changed
- Rename internal schema module from todo_tag_types to issue_tracker_classes for clearer naming
- Rename todo_tag_types_aliases to issue_tracker_aliases to match new naming convention
- Update converters to use IssueTrackerSchema for field keyword enumeration instead of hard-coded list
- Expand package metadata in __about__.py with keywords, license, URLs, and status fields

## [0.1.1] - 2025-07-06
### Fixed
- Issue tracker core functionality restored

## [0.1.0] - 2025-07-06
### Added
- Issue tracker plugin extracted from core pycodetags library
- Support for tracking code issues as a specialized plugin
- Issue tracking and reporting integration

[0.3.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/matthewdeanmartin/pycodetags/releases/tag/v0.1.0
