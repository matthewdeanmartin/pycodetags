# Get the project name from the parent directory
project := `basename $(pwd)`
test_folder := "tests"

# Set up virtual environment handling
venv := if env_var_or_default("VIRTUAL_ENV", "") == "" { "uv run" } else { "" }

# Default recipe
default:
    @just --list

# Install dependencies
uv-install:
    @echo "Installing dependencies"
    uv sync

update-deps:
    @echo "Updating dependencies"
    uv lock
    uv sync
    pre-commit autoupdate
    pre-commit install || true
    @echo "Consider running  pipx upgrade-all"

clean:
    @echo "Removing compiled files"
    pyclean .

# Run tests
test: clean uv-install
    #!/usr/bin/env python
    import toml
    import os
    import subprocess

    # Load the minimum test coverage from pyproject.toml
    config = toml.load('pyproject.toml')
    minimum_coverage = 70 # config['tool']['strict-build-script']['minimum_test_coverage']

    # Set the environment variable for minimum coverage
    os.environ['minimum_coverage'] = str(minimum_coverage)

    # Define the command to run the tests
    command = f"{{venv}} py.test {{test_folder}} -vv --cov={{project}} --cov-report=html --cov-fail-under {minimum_coverage}"

    # Run the command
    subprocess.run(command, shell=True, check=True)


lock:
    uv lock && uv sync

# Format imports
isort:
    @echo "Formatting imports"
    {{venv}} isort .

# Format code
black: isort
    @echo "Formatting code"
    if [ -f loc_{{project}}/__about__.py ]; then cp loc_{{project}}/__about__.py {{project}}/__about__.py; fi
    if [ -d loc_{{project}} ]; then rm -rf loc_{{project}}; fi
    {{venv}} black {{project}} --exclude .venv
    {{venv}} black {{test_folder}} --exclude .venv
    {{venv}} black plugins --exclude .venv
    {{venv}} coderoller-flatten-repo pycodetags


# Run pre-commit checks
pre-commit: isort black
    @echo "Running pre-commit checks"
    {{venv}} pre-commit run --all-files || { echo "First attempt failed, retrying..."; {{venv}} pre-commit run --all-files; }


# Run security checks
bandit:
    @echo "Security checks"
    {{venv}} bandit {{project}} -c pyproject.toml -r

# Run safety check
safety:
    @echo "Running safety check"
    # pipx inject uv uv-plugin-export
    uv export -f requirements.txt --output requirements.txt --without-hashes
    {{venv}} safety check -r requirements.txt
    rm requirements.txt

# Run pylint
pylint: isort black
    @echo "Linting with pylint"
    {{venv}} pylint {{project}} --rcfile=.pylintrc --fail-under 10
    # {{venv}} pylint scripts --rcfile=.pylintrc_scripts --fail-under 8.5
    {{venv}} pylint {{test_folder}} --rcfile=.pylintrc_tests --fail-under 10
    {{venv}} ruff check . --fix --exclude=test_legacy,dead_code

# Run all checks
check: mypy test pylint bandit pre-commit tool-audit

check-deps: lock safety
    echo "Checking dependencies"

# Run mypy
mypy:
    {{venv}} mypy {{project}} --ignore-missing-imports --check-untyped-defs --strict

# Build Docker image
docker:
    docker build -t {{project}} -f Dockerfile .

# Check documentation
check-docs:
    {{venv}} interrogate {{project}} --verbose
    {{venv}} pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

# Generate documentation
make-docs:
    pdoc {{project}} --html -o docs --force

# Check Markdown files
check-md:
    {{venv}} mdformat README.md docs/*.md
    {{venv}} markdownlint README.md --config .markdownlintrc

# Check spelling
spell:
    {{venv}} pylint {{project}} --enable C0401,C0402,C0403 --rcfile=.pylintrc_spell
    {{venv}} codespell README.md --ignore-words=spelling_dictionary.dic
    {{venv}} codespell {{project}} --ignore-words=spelling_dictionary.dic

# Check changelog
check-changelog:
    {{venv}} changelogmanager validate

# Run all checks
check-all: check-docs check-md spell check-changelog


mr: lock safety spell
    @echo "Periodic burdensome checks"


upgrade-all: lock
    pre-commit autoupdate
    pre-commit install || true
    pre-commit run --all-files
    pipx upgrade-all

package-check:
    @echo "Check if pyproject.toml is as good as it can be"
    deptry {{project}} -kf {{project}}


pipx-installs:
    pipx install black
    pipx install isort
    pipx install pylint
    pipx inject pylint pyenchant
    pipx install pyupgrade
    pipx install vulture
    pipx install safety
    pipx install flake8
    pipx inject flake8 dlint mccabe pyflakes pep8-naming flake8-bugbear
    pipx install mypy
    pipx install bandit
    pipx install codespell

tool-audit-freeze:
    cli_tool_audit freeze pipx black isort pylint pyuprade vulture safety flake8 mypy bandit

tool-audit:
    cli_tool_audit audit
