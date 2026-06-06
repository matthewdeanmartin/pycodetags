# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Identity. Important for any database like behaviors in the future
- TDG syntax support. Allows for title/description

### Fixed
- Merging of adjacent tags fixed.


## [0.7.0] - 2025-08-03

### Added

- Data tag mutation API added for adding, removing, changing data tags in a source file.

## [0.6.0] - 2025-07-13

### Added

- Validations show on basic HTML Report
- Convenience functions for interactive use: inspect_file and list_available_schemas
- New dependency on jmespath to allow initial values to be expressions involving other data fields

### Changed

- Submodules namespaces changed with clearer contract on exported functions via dunder __all__
- FolkTag is now just an ingest format

### Fixed

- Most fields now show on basic HTML Report
- Data quality improvements on code tags

## [0.5.0] - 2025-07-07

### Fixed

- Project links
- Folk tags now have correct offsets

## [0.4.0] - 2025-07-06

### Added

- Caching of ast parsing

## [0.3.0] - 2025-07-06

### Added

- Several application plugins
- dumps/loads interface
- pycodetags init command

### Changed

- Huge refactoring into core library and plugins

### Removed

- Issue tracker code (now in pycodetags_issue_tracker)

### Fixed

- Double code tags found when they match two schemas (folk and PEP350)

## [0.2.0] - 2025-06-28

### Added

- Integration tests

### Fixed

- Double code tags found when they match two schemas (folk and PEP350)

## [0.1.2] - 2025-06-26

### Fixed

- Importing colored logging when it isn't available
- Defensive coding on arg parse
- Defensive coding on "can't import"

## [0.1.1] - 2025-06-26

### Added

- Tags: Strongly Type Tags, Folk Tags, PEP 350 Tags
- Tags: Collectors for all three schemas, Converters for text schemas
- Logging: Standard and bug trail logging
- CLI: Report generation
- Docs: Data Model, design, FAQ, Prior Art
- Docs: Changelog, Readme, Authors
- Views: Text, Changelog, HTML, JSON
- Views: Jinja style
- Build: Makefile and Github build script
- Config: TOML driven config
- Feature: Supports context manager tag
- Plugins: Add plugin system
- DATA: a code tag for supporting discussion, data, code review

## [0.1.0] - 2025-06-26

### Added

- Initial release with tags, collectors, and converters

[0.7.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/matthewdeanmartin/pycodetags/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/matthewdeanmartin/pycodetags/releases/tag/v0.1.0
