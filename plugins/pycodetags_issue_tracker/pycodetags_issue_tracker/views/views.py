"""
Given data structure returned by collect submodule, creates human-readable reports.
"""

from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from typing import Any

from pycodetags_issue_tracker import TODO
from pycodetags_issue_tracker.config.issue_tracker_config import get_issue_tracker_config

from pycodetags.views.view_tools import group_and_sort

logger = logging.getLogger(__name__)


def print_validate(found: list[TODO]) -> bool:
    """
    Prints validation errors for TODOs.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    print("TODOs")
    found_problems = False
    total = 0
    for item in sorted(found, key=lambda x: x.code_tag or ""):
        validations = item.validate()
        if validations:
            found_problems = True
            print(item.as_pep350_comment())
            print(item.terminal_link())
            for validation in validations:
                print(f"  {validation}")
            print(f"Original Schema {item.original_schema}")
            print(f"Original Text {item.original_text}")
            # print(item)
            print()
        total += len(validations)
    print(f"Found {total} issues.")
    return found_problems


def print_text(found: list[TODO]) -> None:
    """
    Prints TODOs and Dones in text format.
    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found
    if todos:
        grouped = group_and_sort(
            todos, key_fn=lambda x: x.code_tag or "N/A", sort_items=True, sort_key=lambda x: x.comment or "N/A"
        )
        for tag, items in grouped.items():
            print(f"--- {tag.upper()} ---")
            for todo in items:
                print(todo.as_pep350_comment())
                print(todo.terminal_link())
                print()
    else:
        print("No Code Tags found.")


def print_changelog(found: list[TODO]) -> None:
    """Prints Done items in the 'Keep a Changelog' format.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found

    completed = [task for task in todos if task.is_probably_done()]
    completed.sort(key=lambda task: (task.release or "N/A", str(task.closed_date or "")), reverse=True)
    changelog: dict[str, Any] = defaultdict(lambda: defaultdict(list))
    categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    for task in completed:
        category = next(
            (name for name in categories if name.lower() == (task.change_type or "").strip().lower()),
            "Unclassified",
        )
        changelog[task.release or "N/A"][category].append(task)
    versions = sorted(changelog, reverse=True)

    print("# Changelog\n")
    print("All notable changes to this project will be documented in this file.\n")

    for version in versions:
        first_done = changelog[version][next(iter(changelog[version]))][0]
        if first_done.closed_date and isinstance(first_done.closed_date, (datetime.date, datetime.datetime)):
            version_date = first_done.closed_date.strftime("%Y-%m-%d")
        elif first_done.closed_date:
            version_date = str(first_done.closed_date)
        else:
            version_date = "Unknown date"

        print(f"## [{version}] - {version_date}\n")

        for change_type in [*categories, "Unclassified"]:
            if change_type in changelog[version]:
                print(f"### {change_type}")
                for done in changelog[version][change_type]:
                    description = done.title if done.title is not None else done.comment
                    if done.tracker:
                        ticket_id = done.tracker.split("/")[-1]
                        print(f"- {description} ([{ticket_id}]({done.tracker}))")
                    else:
                        print(f"- {description}")

                print()


def print_todo_md(found: list[TODO]) -> None:
    """
    Outputs TODO and Done items in a markdown board-style format.

    https://github.com/todomd/todo.md?tab=readme-ov-file

    Format:
    # Project Name
    Project Description

    ### Column Name
    - [ ] Task title ~3d #type @name yyyy-mm-dd
      - [ ] Sub-task or description

    ### Completed Column ✓
    - [x] Completed task title
    """
    todos = found

    print("# Code Tags TODO Board")
    print("Tasks and progress overview.\n")
    print("Legend:")
    print("`~` means due")
    print("`@` means assignee")
    print("`#` means category")

    config = get_issue_tracker_config()

    groups: dict[str, list[TODO]] = {status: [] for status in config.valid_status()}
    for task in todos:
        status = (task.status or "").strip().lower()
        if not status:
            status = "done" if task.is_probably_done() else "todo"
        groups.setdefault(status, []).append(task)

    for status, tasks in groups.items():
        print(f"### {status.capitalize()}")
        for task in tasks:
            is_done = task.is_probably_done()
            done_symbol = "[x]" if is_done else "[ ]"
            description = task.title if task.title is not None else task.comment
            task_line = f"- {done_symbol} {description}"
            if not is_done:
                if task.due:
                    task_line += f" ~{task.due}"
                if task.category:
                    task_line += f" #{task.category.lower()}"
                if task.assignee:
                    task_line += f" @{task.assignee}"
            if task.closed_date:
                closed_date = task.closed_date
                if isinstance(closed_date, (datetime.date, datetime.datetime)):
                    closed_date = closed_date.strftime("%Y-%m-%d")
                task_line += f" ({closed_date})"
            print(task_line)


def print_done_file(found: list[TODO]) -> None:
    """
    Structure:
        TODO in comment format.
        Done date + done comment in square bracket
        Blank line

    Problems:
        This will have a problem with comment identity. (which TODO corresponds to which in the DONE file).
        Identity is not a problem for when the TODO is deleted immediately after DONE.txt generation.

    Example:
        # TODO: Recurse into subdirs only on blue
        # moons. <MDE 2003-09-26>
        [2005-09-26 Oops, I underestimated this one a bit.  Should have
        used Warsaw's First Law!]

        # FIXME: ...
        ...

    """
    dones = found
    for done in dones:
        if not done.is_probably_done():
            continue
        # This is valid python. The PEP-350 suggestion was nearly valid python.
        print(done.as_pep350_comment())
        done_date = done.closed_date or ""

        if not done_date:
            after = f", after {done.origination_date}" if done.origination_date else ""
            now = datetime.datetime.now()
            now_day = now.strftime("%Y-%m-%d")
            done_date = f"before {now_day}"
            if after:
                done_date += after
        done_text = f"{done_date} {done.closed_comment or 'no comment'}".strip()
        print(f'["{done_text}"]')
        print()
