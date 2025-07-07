"""
This module provides functionality to render collected TODOs into an HTML report using Jinja2 templates.
"""

from __future__ import annotations

import datetime

from pycodetags_issue_tracker import TODO
from pycodetags_issue_tracker.views.health_o_meter import HealthOMeter

try:
    import importlib_resources as pkg_resources
except ImportError:
    import importlib.resources as pkg_resources

import logging
import os
import webbrowser
from pathlib import Path

import jinja2
import pycodetags_issue_tracker.views.templates as templates  # make sure templates is a real subpackage

logger = logging.getLogger(__name__)


def print_html(found: list[TODO], output: Path = Path("issues_site")) -> None:
    """Generate an HTML report from collected TODOs.

    Args:
        found (CollectedTODOs): An instance of CollectedTODOs containing the collected TODOs.
        output (Path): The directory where the HTML report will be saved. Defaults to "issues_site".
    """
    # Load template from package
    with pkg_resources.files(templates).joinpath("report.html.jinja2").open("r", encoding="utf-8") as f:
        template_src = f.read()

    # Render HTML with data
    template = jinja2.Template(template_src)
    total_to_render = len(found)
    logger.info(f"Total to render: {total_to_render}")
    if total_to_render == 0:
        raise TypeError("No data to render.")

    logger.info(f"Rendering {total_to_render} TODOs and Dones into HTML report.")

    health_o_meter = HealthOMeter(found)
    metrics = health_o_meter.calculate_metrics()


    dones = list(_ for _ in found if _.is_probably_done())
    todos = list(_ for _ in found if not _.is_probably_done())
    rendered = template.render(
        now=datetime.datetime.now().date(),
        dones=dones,
        todos=todos,
        exceptions=[],
        undefined=jinja2.StrictUndefined,
        metrics=metrics,
    )

    # Ensure output directory exists
    output.mkdir(parents=True, exist_ok=True)

    # Write rendered HTML to index.html in output dir
    output_file = output / "index.html"
    output_file.write_text(rendered, encoding="utf-8")

    # Skip browser launch if on CI (e.g., GitHub Actions, etc.)
    if not any(key in os.environ for key in ("CI", "GITHUB_ACTIONS", "PYCODETAGS_NO_OPEN_BROWSER")):
        webbrowser.open(output_file.resolve().as_uri())
