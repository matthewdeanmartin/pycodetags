# =====================================
# 🛠️  Makefile for MkDocs in /docs/
# =====================================

# Paths
MKDOCS_CONFIG := ../mkdocs.yml
SITE_DIR := ../site
DOCS_DIR := .
MARKDOWN_FILES := $(shell find $(DOCS_DIR) -name '*.md')

# -------------------------------------
# 🧽 Help: List available targets
# -------------------------------------
.PHONY: help
help:
	@echo ""
	@echo "📚  MkDocs Documentation Commands"
	@echo ""
	@echo "  make serve     🔄 Serve the docs locally with live reload"
	@echo "  make build     🏗️  Build the static site to ../site/"
	@echo "  make clean     🧹 Delete the generated site directory"
	@echo "  make lint      🔍 Lint markdown files using markdownlint"
	@echo "  make doctor    🚑 Run mkdocs doctor to check config & links"
	@echo ""

# -------------------------------------
# 🚀 Serve: Run the local dev server
# -------------------------------------
.PHONY: serve
serve:
	mkdocs serve --config-file $(MKDOCS_CONFIG)

# -------------------------------------
# 🔨 Build: Generate the static site
# -------------------------------------
.PHONY: build
build:
	mkdocs build --clean --config-file $(MKDOCS_CONFIG)

# -------------------------------------
# 🧽 Clean: Remove the site/ output
# -------------------------------------
.PHONY: clean
clean:
	rm -rf $(SITE_DIR)

# -------------------------------------
# 🔍 Lint: Check Markdown formatting
# Requires: npm install -g markdownlint-cli
# -------------------------------------
.PHONY: lint
lint:
	mdformat *.md
	markdownlint *.md # $(MARKDOWN_FILES)
	linkcheckMarkdown .

# -------------------------------------
# 🚑 Doctor: Validate mkdocs setup (broken links, config, etc.)
# -------------------------------------
.PHONY: doctor
doctor: build
	@echo "🔗 Running link checker on built site…"
	# Example: check all links in the site/ directory (install linkchecker beforehand)
	linkchecker --ignore-url='/localhost:' ../site