.EXPORT_ALL_VARIABLES:
# Get changed files

FILES := $(wildcard **/*.py)

# if you wrap everything in uv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

uv.lock: pyproject.toml
	@echo "Installing dependencies"
	@uv sync

clean-pyc:
	@echo "Removing compiled files"


clean-test:
	@echo "Removing coverage data"
	@rm -f .coverage || true
	@rm -f .coverage.* || true

clean: clean-pyc clean-test

# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test: clean uv.lock install_plugins
	@echo "Running unit tests"
	$(VENV) pytest --doctest-modules pycodetags
	# $(VENV) python -m unittest discover
	$(VENV) py.test tests -vv -n 2 --cov=pycodetags --cov-report=html --cov-fail-under 50 --cov-branch --cov-report=xml --junitxml=junit.xml -o junit_family=legacy
	$(VENV) bash basic_test.sh
	$(VENV) bash basic_test_with_logging.sh
#	$(VENV) bash basic_plugins.sh
#	$(VENV) bash basic_test_via_config.sh
#	$(VENV) bash basic_test_with_multiple_sources.sh


.build_history:
	@mkdir -p .build_history

.build_history/isort: .build_history $(FILES)
	@echo "Formatting imports"
	$(VENV) isort .
	@touch .build_history/isort

.PHONY: isort
isort: .build_history/isort

.build_history/black: .build_history .build_history/isort $(FILES)
	@echo "Formatting code"
	$(VENV) metametameta pep621
	$(VENV) black pycodetags # --exclude .venv
	$(VENV) black tests # --exclude .venv
	$(VENV) black demo # --exclude .venv
	$(VENV) black scripts # --exclude .venv
	@touch .build_history/black
	$(VENV) ./make_prompt.sh

.PHONY: black
black: .build_history/black

.build_history/pre-commit: .build_history .build_history/isort .build_history/black
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files
	@touch .build_history/pre-commit

.PHONY: pre-commit
pre-commit: .build_history/pre-commit

.build_history/bandit: .build_history $(FILES)
	@echo "Security checks"
	$(VENV)  bandit pycodetags -r
	@touch .build_history/bandit

.PHONY: bandit
bandit: .build_history/bandit

.PHONY: pylint
.build_history/pylint: .build_history .build_history/isort .build_history/black $(FILES)
	@echo "Linting with pylint"
	$(VENV) ruff --fix
	$(VENV) pylint pycodetags --fail-under 9.8
	@touch .build_history/pylint

# for when using -j (jobs, run in parallel)
.NOTPARALLEL: .build_history/isort .build_history/black

check: mypy test pylint bandit pre-commit

#.PHONY: publish_test
#publish_test:
#	rm -rf dist && poetry version minor && poetry build && twine upload -r testpypi dist/*

.PHONY: publish
publish: test
	rm -rf dist && hatch build

.PHONY: mypy
mypy:
	$(VENV) echo $$PYTHONPATH
	$(VENV) mypy pycodetags --ignore-missing-imports --check-untyped-defs


check_docs:
	$(VENV) interrogate pycodetags --verbose
	$(VENV) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

make_docs:
	pdoc pycodetags --html -o docs --force

check_md:
	$(VENV) mdformat README.md docs/*.md
	$(VENV) linkcheckMarkdown README.md
	$(VENV) markdownlint README.md --config .markdownlintrc

check_spelling:
	$(VENV) pylint pycodetags --enable C0402 --rcfile=.pylintrc_spell
	$(VENV) codespell README.md --ignore-words=private_dictionary.txt
	$(VENV) codespell pycodetags --ignore-words=private_dictionary.txt

check_changelog:
	# pipx install keepachangelog-manager
	$(VENV) changelogmanager validate

check_all_docs: check_docs check_md check_spelling check_changelog

check_own_ver:
	# Can it verify itself?
	$(VENV) ./dog_food.sh

#audit:
#	# $(VENV) python -m pycodetags audit
#	$(VENV) tool_audit single pycodetags --version=">=2.0.0"

install_plugins:
	# right now, only plugins that have no cross dependencies!
	# Apps
	uv pip install -e plugins/pycodetags_issue_tracker
	uv pip install -e plugins/pycodetags_chat
	# TODO: docs and code review
	# depends on issue tracker in own namespace
	uv pip install -e plugins/pycodetags_issue_tracker_gh_sync
	# pure data plugins
	uv pip install -e plugins/pycodetags_universal
	uv pip install -e plugins/pycodetags_to_sqlite

.PHONY: issues
issues:
	uv pip install -e plugins/pycodetags_issue_tracker
	@echo "Checking issues"
	# $(VENV)	pycodetags data --src pycodetags --src plugins --format json>issues_site/data.json
	@echo "Current issues:"
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format text
	@echo "For best results, fix these issues:"
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format validate
	@echo "Generating HTML report"
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format html>issues_site/index.html
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format changelog>CHANGELOG_DRAFT.md
