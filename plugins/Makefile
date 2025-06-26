test:
	@echo "Running unit tests"
	uv run pytest --doctest-modules pycodetags
	# uv run python -m unittest discover
	uv run py.test tests -vv -n 2 --cov=pycodetags --cov-report=html --cov-fail-under 70
	uv run bash basic_test.sh
	uv run bash basic_plugins.sh
	uv run bash basic_test_with_logging.sh
	uv run bash basic_test_via_config.sh
	uv run bash basic_test_with_multiple_sources.sh


.PHONY: isort
isort:
	@echo "Formatting imports"
	uv run isort .
	@touch .build_history/isort

.PHONY: black
black: isort
	@echo "Formatting code"
	uv run black pycodetags --exclude .venv
	uv run black tests --exclude .venv
	# uv run black scripts --exclude .venv
	uv run coderoller-flatten-repo pycodetags

.PHONY: pre-commit
pre-commit: isort black
	@echo "Pre-commit checks"
	uv run pre-commit run --all-files

.PHONY: bandit
bandit:
	@echo "Security checks"
	uv run  bandit pycodetags -r

.PHONY: pylint
pylint: isort black
	@echo "Linting with pylint"
	uv run ruff --fix
	uv run pylint pycodetags --fail-under 9.8

# for when using -j (jobs, run in parallel)
.NOTPARALLEL: isort black pylint pre-commit

check: mypy test pylint bandit pre-commit

#.PHONY: publish_test
#publish_test:
#	rm -rf dist && poetry version minor && poetry build && twine upload -r testpypi dist/*

.PHONY: publish
publish: test
	rm -rf dist && poetry build

.PHONY: mypy
mypy:
	uv run mypy pycodetags --ignore-missing-imports --check-untyped-defs


check_docs:
	uv run interrogate pycodetags --verbose
	uv run pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

make_docs:
	pdoc pycodetags --html -o docs --force

check_md:
	uv run mdformat README.md docs/*.md
	uv run linkcheckMarkdown README.md
	uv run markdownlint README.md --config .markdownlintrc

check_spelling:
	uv run pylint pycodetags --enable C0402 --rcfile=.pylintrc_spell
	uv run codespell README.md --ignore-words=private_dictionary.txt
	uv run codespell pycodetags --ignore-words=private_dictionary.txt

check_changelog:
	# pipx install keepachangelog-manager
	uv run changelogmanager validate

check_all_docs: check_docs check_md check_spelling check_changelog
