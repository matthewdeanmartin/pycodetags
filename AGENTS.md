# AGENTS

This repository holds the core `pycodetags` library. Work in the `pycodetags/` package and its tests in `tests/`; plugin code in `plugins/` is out of scope unless explicitly requested.

## Style
- Target Python 3.7+ (tests run on 3.8 and 3.13) and keep code compatible with the lowest supported version.
- Format Python code with `black` (line length 120) and organize imports with `isort`.
- Keep commits focused and write clear commit messages.

## Quality checks
Before committing:
1. Run formatting and linting for modified files:
   ```bash
   pre-commit run --files <files>
   ```
2. Run the test suite on Python 3.8 and 3.13:
   ```bash
   tox -e py38
   tox -e py313
   ```

## Documentation
- Add or update docstrings and README/docs when behaviour changes.

