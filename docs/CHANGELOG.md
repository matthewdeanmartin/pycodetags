# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

- Added for new features.
- Changed for changes in existing functionality.
- Deprecated for soon-to-be removed features.
- Removed for now removed features.
- Fixed for any bug fixes.
- Security in case of vulnerabilities.

## [0.6.0] - 2025-07-13

### Added

- Validations show on basic HTML Report
- Convenience functions for interactive use `inspect_file` and `list_available_schemas`
- New dependency on jmespath to allow for initial values to be expressions involving other data fields

### Changed
- (sub)modules namespaces changed, clearer contract on exported functions via dunder `all`

### Fixed

- Most fields now show on basic HTML Report

## [0.5.0] - 2025-07-06

### Fixed

- Project links
- Folk tags now have correct offsets

## [0.4.0] - 2025-07-06

### Added

- Caching of ast parsing

## [0.3.0] - 2025-06-28

### Added

- Several "application" plugins
- dumps/loads interface
- `pycodetags init` command

## Changed

- Huge refactoring into core library and plugins.

## Removed

- Issue tracker code. Now in pycodetags_issue_tracker.

### Fixed

- Double code tags found when they match two schemas (folk and PEP350)

## [0.2.0] - 2025-06-28

## Added

- Integration tests

### Fixed

- Double code tags found when they match two schemas (folk and PEP350)

## [0.1.2] - 2025-06-26

## Fixed

- Importing colored logging when it isn't available.
- Defensive coding on arg parse
- Defensive coding on "can't import"

## [0.1.1] - 2025-06-05

### Added

- Tags: Strongly Type Tags, Folk Tags, PEP 350 Tags
- Tags: Collectors for all three schemas. Converters for text schemas.
- Logging: Standard and bug trail logging
- CLI: Report generation
- Docs: Data Model, design, FAQ, Prior Art
- Docs: Changelog, Readme, Authors
- Views: Text, Changelog, HTML, JSON
- Views: Jinja style
- Build: Makefile and Github build script
- Config: TOML driven config.
- Feature: Supports context manager tag
- Plugins: Add plugin system
- DATA: a code tag for supporting discussion, data, code review, etc.

## [Unreleased]

### Changes

- Refactor issue tracker to a plugin to make core library strictly an abstract code tag (data tags)
