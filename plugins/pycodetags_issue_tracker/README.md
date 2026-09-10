# Release 0.4 compatibility

Requires pycodetags 0.8.x and Python 3.9–3.15. Select `schema = "TDG"`, `"PEP350"`, or this
plugin's `"TODO"` schema explicitly under `[tool.pycodetags]`. TODO uses extended PEP-350.
`pycodetags issues` respects that selection; TDG is owned by the core, not registered by this plugin.
Conversions preserve titles, bodies, local IDs, schema selection, and mutation fingerprints.
`issue` is a parent relationship; `tracker` may be shared by several independently identified tags.
HTML reports honor `--output`; set `PYCODETAGS_NO_OPEN_BROWSER=1` for unattended use.

# Issue Tracker

This is a PEP350 inspired issue tracker. Store issues in source code.

```python
# TODO: Fix this code <matth 2025-07-05 category=math priority=high release=2.01>
```

Also supports advanced scenarios with TODOs as Objects, Decorators, etc.

## Installation

```bash
pip install pycodetags pycodetags-issue-tracker
```

```bash
pipa install pycodetags 
pipx inject pycodetags pycodetags-issue-tracker
```

## Usage

Basic usage is to generate a TODO report and website.

```makefile
.PHONY: issues
issues:install_plugins
	@echo "Checking issues"
	$(VENV)	pycodetags data --src pycodetags --src plugins --format json>issues_site/data.json
	@echo "Current issues:"
	$(VENV) pycodetags issues --src pycodetags --src plugins --format text
	@echo "For best results, fix these issues:"
	$(VENV) pycodetags issues --src pycodetags --src plugins --format validate
	@echo "Generating HTML report"
	$(VENV) pycodetags issues --src pycodetags --src plugins --format html
```

## Prior Art

PEPs and Standard Library Prior Art

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/) Rejected proposal, now implemented, mostly by `pycodetags`

## Documentation

- [Readthedocs](https://pycodetags.readthedocs.io/en/latest/)

## Project Links

- [GitHub](https://github.com/matthewdeanmartin/pycodetags)
- [PyPI](https://pypi.org/project/pycodetags-issue-tracker/)
- [Bug Tracker](https://github.com/matthewdeanmartin/pycodetags/issues)
