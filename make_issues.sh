set -euo pipefail

pycodetags data --src pycodetags --src plugins --format json>issues_site/data.json

pycodetags issues --src pycodetags --src plugins --format text

pycodetags issues --src pycodetags --src plugins --format validate
pycodetags issues --src pycodetags --src plugins --format html>issues_site/index.html