# AGENTS

Working on stomping out all variables with names starting with `_`. Do not do any sort of hungarian notation.

_ means unused and prefix with _ means unused. It doesn't mean private. Don't name any method with _ Ever. I'm serious.

This repository holds the core `pycodetags` library. Work in the `pycodetags/` package and its tests in `tests/`; plugin code in `plugins/` is out of scope unless explicitly requested.

## Style
- Use Python 3.14 locally. Support Python 3.9 through 3.15 and keep code compatible with Python 3.9.
- Format Python code with `black` (line length 120) and organize imports with `isort`.
- Keep commits focused and write clear commit messages.

## Quality checks
Before committing:
1. Run formatting and linting for modified files:
   ```bash
   pre-commit run --files <files>
   ```
2. Run the test suite across the supported Python versions:
   ```bash
   tox -e py39,py310,py311,py312,py313,py314,py315
   ```

## Documentation
- Add or update docstrings and README/docs when behaviour changes.

