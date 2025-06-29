# code_tags_jira_sync.py
import argparse
import logging

import pluggy
from pycodetags_issue_tracker import TODO

from pycodetags.config import CodeTagsConfig

logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("pycodetags")


@hookimpl
def code_tags_add_cli_subcommands(subparsers: argparse._SubParsersAction) -> None:
    jira_parser = subparsers.add_parser("github-issues-sync", help="Synchronize TODOs with GH Issues")
    jira_parser.add_argument("--project", required=True, help="Project key")
    jira_parser.add_argument("--issue-type", default="Task", help="Issue type for new TODOs")
    jira_parser.add_argument(
        "--dry-run", action="store_true", help="Do not create/update issues, just show what would happen"
    )
    # Add more Jira-specific arguments as needed
    return jira_parser


@hookimpl
def code_tags_run_cli_command(
    command_name: str,
    args: argparse.Namespace,
    found_data: list[TODO],
    config: CodeTagsConfig,  # pylint: disable=unused-argument
) -> bool:
    if command_name == "github-issues-sync":
        print(f"Running GH Issues synchronization for project: {args.project}")
        if args.dry_run:
            print("Dry run enabled. No changes will be made to Github.")

        # Example: Process TODOs from found_data and interact with Jira
        for todo in found_data:
            # In a real scenario, you'd use the jira-python library here
            print(f"  Processing TODO: {todo.comment}")
            # Simulate Github interaction
            if not args.dry_run:
                # jira_client.create_issue(project=args.project, summary=todo.comment, ...)
                print(f"    Would create Github issue for: {todo.comment}")
            else:
                print(f"    (Dry Run) Would create Github issue for: {todo.comment}")
        return True  # Indicates this plugin handled the command
    return False  # This plugin does not handle the requested command
