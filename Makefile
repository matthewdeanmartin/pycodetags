.EXPORT_ALL_VARIABLES:

# if you wrap everything in uv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

CHANGELOGMANAGER = $(VENV) kaclm --config pyproject.toml

uv.lock: pyproject.toml
	@echo "Installing dependencies"
	@uv sync


# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test: uv.lock install_plugins
	@echo "Running unit tests"
	$(VENV) pytest --doctest-modules pycodetags
	# $(VENV) python -m unittest discover
	$(VENV) py.test tests -vv -n 2 --cov=pycodetags --cov-report=html --cov-fail-under 50 --cov-branch --cov-report=xml --junitxml=junit.xml -o junit_family=legacy
	$(VENV) bash basic_test.sh
	$(VENV) bash basic_test_with_logging.sh
#	$(VENV) bash basic_plugins.sh
#	$(VENV) bash basic_test_via_config.sh
#	$(VENV) bash basic_test_with_multiple_sources.sh



isort:
	@echo "Formatting imports"
	$(VENV) isort .

black: isort
	@echo "Formatting code"
	$(VENV) metametameta pep621
	$(VENV) black pycodetags # --exclude .venv
	$(VENV) black tests # --exclude .venv
	$(VENV) black demo # --exclude .venv
	$(VENV) black scripts # --exclude .venv
	# $(VENV) ./make_prompt.sh

pre-commit: isort black
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files


bandit:
	@echo "Security checks"
	$(VENV) bandit pycodetags -r

pylint: isort black
	@echo "Linting with pylint"
	$(VENV) ruff check --fix
	$(VENV) pylint pycodetags --fail-under 9.8

check: mypy test pylint bandit check-dist

# ── Distribution verification ────────────────────────────────────────────────

.PHONY: check-dist
check-dist:
	@echo "Verifying distribution contents"
	@python -c "import shutil; shutil.rmtree('.build/dist-check', ignore_errors=True)"
	uv build --out-dir .build/dist-check --no-sources
	$(VENV) python scripts/verify_distribution.py .build/dist-check

# ── Python 3.15 trial run ────────────────────────────────────────────────────
# Uses a dedicated venv so the normal .venv is never clobbered.
# See python315.md. Core deps + plugins + dev group all resolve on 3.15.

PY315 := 3.15.0rc2
VENV315 := .venv315rc2
PY315_EXE := $(VENV315)/Scripts/python.exe

.PHONY: venv315
venv315:
	@echo "Creating Python $(PY315) trial venv at $(VENV315)"
	@test -x $(PY315_EXE) || uv venv $(VENV315) --python $(PY315)
	uv pip install -e . --group dev --python $(PY315_EXE)
	uv pip install -e plugins/pycodetags_issue_tracker --python $(PY315_EXE)
	uv pip install -e plugins/pycodetags_chat --python $(PY315_EXE)
	uv pip install -e plugins/pycodetags_issue_tracker_gh_sync --python $(PY315_EXE)
	uv pip install -e plugins/pycodetags_universal --python $(PY315_EXE)
	uv pip install -e plugins/pycodetags_to_sqlite --python $(PY315_EXE)

.PHONY: venv315-clean
venv315-clean:
	@echo "Recreating Python $(PY315) trial venv from scratch"
	uv venv $(VENV315) --python $(PY315) --clear
	@$(MAKE) venv315

.PHONY: test315
test315: venv315
	@echo "Running unit tests on Python $(PY315)"
	$(PY315_EXE) -m pytest --doctest-modules pycodetags
	$(PY315_EXE) -m pytest tests -vv -n 2 --timeout=180
	# $(CURDIR) is a Windows-style path (C:/...) under Git Bash make; the drive
	# colon would split PATH, so convert to a POSIX path inside the shell.
	bash -c 'PATH="$$(cd $(VENV315)/Scripts && pwd):$$PATH"; export PATH; bash basic_test.sh'
	bash -c 'PATH="$$(cd $(VENV315)/Scripts && pwd):$$PATH"; export PATH; bash basic_test_with_logging.sh'

.PHONY: test315-plugins
test315-plugins: venv315
	@echo "Running plugin test suites on Python $(PY315)"
	@for p in pycodetags_chat pycodetags_issue_tracker pycodetags_issue_tracker_gh_sync \
	          pycodetags_to_sqlite pycodetags_universal; do \
		echo "--- $$p"; \
		( cd plugins/$$p && $(CURDIR)/$(PY315_EXE) -m pytest tests -q --timeout=180 ) || exit 1; \
	done

.PHONY: check315
check315: test315 test315-plugins
	@echo "Python $(PY315) checks passed."


publish: test
	rm -rf dist && uv run hatch build

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
	$(CHANGELOGMANAGER) --error-format github validate --all

.PHONY: draft-release
draft-release:
	@if [ -z "$(REPOSITORY)" ]; then echo "REPOSITORY must be set, e.g. owner/repo"; exit 1; fi
	$(CHANGELOGMANAGER) github-release --repository "$(REPOSITORY)"

.PHONY: release-bump
release-bump:
	@if [ -z "$(RELEASE_VERSION)" ]; then echo "RELEASE_VERSION must be set, e.g. 0.7.1"; exit 1; fi
	$(CHANGELOGMANAGER) release --override-version "$(RELEASE_VERSION)" --bump-versions --yes

check_all_docs: check_docs check_md check_spelling check_changelog

check_own_ver:
	# Can it verify itself?
	$(VENV) ./dog_food.sh

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
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format html
	$(VENV) pycodetags issues --src pycodetags --src plugins/pycodetags_issue_tracker/pycodetags_issue_tracker --format changelog>CHANGELOG_DRAFT.md

# ── Dogfooding targets (independent, not wired into check) ───────────────────

.PHONY: version-check
version-check:
	@uv run jiggle_version check

.PHONY: dev-status
dev-status:
	@uv run troml-dev-status validate .

.PHONY: prerelease-check
prerelease-check: version-check dev-status check_changelog
	@echo "Pre-release checks passed."

.PHONY: dont-be-lazy
dont-be-lazy:
	@uv run dont_be_lazy --root . --no-color summary
	@uv run dont_be_lazy --root . --no-color scan pycodetags --no-config-suppressions || true

.PHONY: pydoc-docs
pydoc-docs:
	@uv run pydoc_fork pycodetags -o ./pydoc/
