# AGENTS

This repository holds the core `pycodetags` library. Follow these guidelines when modifying files in this repo.

## Scope
- Focus on the main library in `pycodetags/` and its tests in `tests/`.
- Do **not** modify files inside `plugins/` unless explicitly requested.

## Style
- Target Python 3.7+ and keep code compatible with the lowest supported version.
- Format Python code with `black` (line length 120) and organize imports with `isort`.
- Keep commits focused and use conventional commit-style messages when possible.

## Quality checks
Before committing:
1. Run formatting and linting:
   ```bash
   just pre-commit
   ```
2. Run the test suite with coverage:
   ```bash
   just test
   ```

## Documentation
- Add or update docstrings and README/docs when behaviour changes.

