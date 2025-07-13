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
        total+= len(validations)
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
                print()
    else:
        print("No Code Tags found.")


def print_changelog(found: list[TODO]) -> None:
    """Prints Done items in the 'Keep a Changelog' format.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found

    dones_meta = [d.todo_meta for d in todos if d.is_probably_done()]

    # Deal with dodgy data because validation is optional
    for done in dones_meta:
        if done and not done.release:
            done.release = "N/A"

    # BUG: This probably isn't he right way to sort a version <matth 2024-07-04 category:views status:development
    # priority:low release:1.0.0 iteration:1>
    dones_meta.sort(
        key=lambda d: ((d.release if d.release else "N/A", d.closed_date if d.closed_date else "") if d else ("", "")),
        reverse=True,
    )

    changelog: dict[str, Any] = defaultdict(lambda: defaultdict(list))

    versions = sorted(list({d.release or "N/A" for d in dones_meta if d}), reverse=True)

    for done in dones_meta:
        if done:
            changelog[done.release or ""][done.change_type or "Add"].append(done)

    print("# Changelog\n")
    print("All notable changes to this project will be documented in this file.\n")

    for version in versions:
        first_done = changelog[version][next(iter(changelog[version]))][0]
        if first_done.closed_date and isinstance(first_done.closed_date, (datetime.date, datetime.datetime)):
            version_date = first_done.closed_date.strftime("%Y-%m-%d")
        else:
            version_date = "Unknown date"

        print(f"## [{version}] - {version_date}\n")

        for change_type in ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]:
            if change_type in changelog[version]:
                print(f"### {change_type}")
                for done in changelog[version][change_type]:
                    if done.tracker:
                        ticket_id = done.tracker.split("/")[-1]
                        print(f"- {done.comment} ([{ticket_id}]({done.tracker}))")
                    else:
                        print(f"- {done.comment}")

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

    custom_status = config.valid_status()
    closed_status = config.closed_status()
    if not custom_status:
        custom_status = ["TODO", "DONE"]

    # HACK: This works poorly when statuses are missing or if they don't sync up with the code tag.<matth 2025-07-04
    # category:views priority:low status:development release:1.0.0 iteration:1>

    for status in custom_status:
        print(f"### {status.capitalize()}")
        is_done = False
        if status in closed_status:
            done_symbol = "[x]"
            is_done = True
        else:
            done_symbol = "[ ]"
        for todo in todos:
            if todo.status == status or (todo.code_tag and todo.code_tag.lower() == status):
                meta = todo.todo_meta
                if not meta:
                    continue
                task_line = f"- {done_symbol} {meta.comment}"
                if not is_done:
                    if meta.due:
                        task_line += f" ~{meta.due}"
                    if meta.category:
                        task_line += f" #{meta.category.lower()}"
                    if meta.assignee:
                        task_line += f" @{meta.assignee}"
                if meta.closed_date and isinstance(meta.closed_date, (datetime.date, datetime.datetime)):
                    task_line += f" ({meta.closed_date.strftime('%Y-%m-%d')})"
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
