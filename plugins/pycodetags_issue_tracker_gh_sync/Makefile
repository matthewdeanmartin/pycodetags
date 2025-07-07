# if you wrap everything in uv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test:
	@echo "Running unit tests"
	# $(VENV) pytest --doctest-modules pycodetags_github_issues_sync
	# $(VENV) python -m unittest discover
	$(VENV) PYTHONPATH=$PYTHONPATH:. coverage run --source=pycodetags_github_issues_sync -m pytest tests -vv
	$(VENV) coverage html
	$(VENV) coverage report --fail-under=0
	# $(VENV) bash basic_test.sh

.PHONY: black
black:
	@echo "Formatting code"
	$(VENV) metametameta pep621
	$(VENV) isort .
	$(VENV) black pycodetags_github_issues_sync # --exclude .venv
	$(VENV) black tests # --exclude .venv
	$(VENV) coderoller-flatten-repo pycodetags_github_issues_sync

.PHONY: bandit
bandit:
	@echo "Security checks"
	$(VENV)  bandit pycodetags_github_issues_sync -r

.PHONY: pylint
pylint: black
	@echo "Linting with pylint"
	$(VENV) ruff check --fix
	$(VENV) pylint pycodetags_github_issues_sync --fail-under 9.8


check: mypy test pylint bandit

#.PHONY: publish_test
#publish_test:
#	rm -rf dist && poetry version minor && poetry build && twine upload -r testpypi dist/*

.PHONY: publish
publish: test
	rm -rf dist && hatch build

.PHONY: mypy
mypy:
	$(VENV) mypy pycodetags_github_issues_sync --ignore-missing-imports --check-untyped-defs


check_docs:
	$(VENV) interrogate pycodetags_github_issues_sync --verbose
	$(VENV) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

make_docs:
	pdoc pycodetags_github_issues_sync --html -o docs --force

check_md:
	$(VENV) mdformat README.md docs/*.md
	$(VENV) linkcheckMarkdown README.md
	$(VENV) markdownlint README.md --config .markdownlintrc

check_spelling:
	$(VENV) pylint pycodetags_github_issues_sync --enable C0402 --rcfile=.pylintrc_spell
	$(VENV) codespell README.md --ignore-words=private_dictionary.txt
	$(VENV) codespell pycodetags_github_issues_sync --ignore-words=private_dictionary.txt

check_changelog:
	# pipx install keepachangelog-manager
	$(VENV) changelogmanager validate

check_all_docs: check_docs check_md check_spelling check_changelog
