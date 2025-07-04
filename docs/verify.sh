#!/bin/bash
set -euo pipefail

echo
echo "Formatting markdown files with mdformat"
echo
for file in $FILES; do
    uv run mdformat "$file"
done

echo
echo "Are the links okay?"
echo
uv run linkcheckMarkdown content
