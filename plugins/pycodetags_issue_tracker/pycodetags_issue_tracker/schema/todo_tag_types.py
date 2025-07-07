"""
Strongly typed code tag types.
"""

from __future__ import annotations

import datetime
import logging
import os
import warnings
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, cast  # noqa

from pycodetags_issue_tracker.config.issue_tracker_config import get_issue_tracker_config
from pycodetags_issue_tracker.schema.issue_tracker_schema import IssueTrackerSchema
from pycodetags_issue_tracker.schema.todo_object_schema import TODO_KEYWORDS

from pycodetags.app_config.config import get_code_tags_config
from pycodetags.data_tags.data_tags_classes import DATA

try:
    from typing import Literal  # type:ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type:ignore[assignment,unused-ignore] # noqa


logger = logging.getLogger(__name__)


class DueException(Exception):
    pass


def parse_due_date(date_str: str) -> datetime.datetime:
    """
    Parses a date string in the format 'YYYY-MM-DD' and returns a datetime object.

    Args:
        date_str (str): The date string to parse.

    Returns:
        datetime.datetime: The parsed datetime object.

    Raises:
        ValueError: If the date string is not in the format 'YYYY-MM-DD'.

    Examples:
        >>> parse_due_date("2023-10-01")
        datetime.datetime(2023, 10, 1, 0, 0)

        >>> parse_due_date("invalid-date")
        Traceback (most recent call last):
        ...
        ValueError: Invalid date format for due_date: 'invalid-date'. Use YYYY-MM-DD.
    """
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Invalid date format for due_date: '{date_str}'. Use YYYY-MM-DD.") from e


@dataclass
class TODO(DATA):
    """
    Represents a TODO item with various metadata fields.
    """

    assignee: str | None = None
    """User who will do the work"""
    originator: str | None = None
    """User who created the issue"""

    # Due fields
    origination_date: str | None = None
    """Date issue created in YYYY-MM-DD format"""
    due: str | None = None
    """Date issue will be done in YYYY-MM-DD format"""
    release_due: str | None = None
    """Release due, will attempt to parse as semantic version A.B.C"""
    release: str | None = None
    """Release completed, will attempt to parse as semantic version A.B.C"""
    iteration: str | None = None
    """User specified meaning, a milestone in a release"""

    # Done fields
    change_type: str | None = None
    """Field for Keepachangelog support"""
    closed_date: str | None = None
    """Date issue closed in YYYY-MM-DD format"""
    closed_comment: str | None = None

    # Integration fields
    tracker: str | None = None
    """A URL or Issue as determined by config or URL detection"""

    priority: str | None = None
    """User specified meaning, urgency of task"""
    status: str | None = None
    """Done, plus other user specified values"""
    category: str | None = None
    """User specified meaning, any useful categorization of issues"""

    # Internal state
    _due_date_obj: datetime.datetime | None = field(init=False, default=None)
    """Strongly typed due_date"""

    todo_meta: TODO | None = field(init=False, default=None)
    """Necessary internal field for decorators"""

    def disable_behaviors(self) -> bool:
        """Don't do anything because we are in CI, production, end users machine or we just aren't using
        the action feature
        """
        config = get_code_tags_config()
        if (
            config.disable_all_runtime_behavior()
            or not config.enable_actions()
            or config.disable_on_ci()
            and "CI" in os.environ
        ):
            return True
        return False

    def __post_init__(self) -> None:
        """
        Validation and complex initialization
        """
        if self.disable_behaviors():
            return

        if self.due:
            # TODO: find better way to upgrade string to strong type (date/int).
            #  <matth 2025-07-04 status:development category:parser priority:high release:1.0.0 iteration:1>
            try:
                parsed_date = parse_due_date(self.due)
                self._due_date_obj = parsed_date
            except ValueError:
                pass

        self.todo_meta = self

    def is_probably_done(self) -> bool:
        config = get_issue_tracker_config()
        date_is_done = bool(self.closed_date)
        status_is_done = bool(self.status) and (self.status or "").lower() in config.closed_status()

        return date_is_done or status_is_done

    @property
    def current_user(self) -> str:
        config = get_issue_tracker_config()
        return config.current_user()

    def _is_condition_met(self) -> bool:
        """Checks if the conditions for triggering an action are met."""
        if self.disable_behaviors():
            return False

        is_past_due = bool(self._due_date_obj and datetime.datetime.now() > self._due_date_obj)

        user_matches = self.assignee.lower() == self.current_user.lower() if self.assignee else False
        config = get_issue_tracker_config()

        on_past_due = config.action_on_past_due()
        only_on_user_match = config.action_only_on_responsible_user()

        if on_past_due and not only_on_user_match:
            return is_past_due and user_matches
        if on_past_due:
            return is_past_due
        if only_on_user_match and user_matches:
            return user_matches
        return False

    def _perform_action(self) -> None:
        """Performs the configured action if conditions are met."""
        if self.disable_behaviors():
            return

        if self._is_condition_met():
            config = get_code_tags_config()
            action = config.default_action().lower()
            message = f"TODO Reminder: {self.comment} (assignee: {self.assignee}, due: {self.due})"
            if action == "stop":
                raise DueException(message)
            if action == "warn":
                warnings.warn(message, stacklevel=3)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
            self._perform_action()
            return cast(Callable[..., Any], func(*args, **kwargs))

        cast(Any, wrapper).todo_meta = self
        return wrapper

    def __enter__(self) -> TODO:
        self._perform_action()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> Literal[False]:
        return False  # propagate exceptions

    def validate(self) -> list[str]:
        """Validates the TODO item.

        Only developer tooling should call this.
        """
        config = get_issue_tracker_config()

        issues = []
        # Required if done to support features
        if self.is_probably_done():
            if not self.assignee:
                issues.append("Item is done, missing assignee")
            if not self.release:
                valid_releases = config.valid_releases()
                if valid_releases:
                    issues.append(f"Item is done, missing release, suggest {valid_releases}")
                else:
                    issues.append("Item is done, missing release (version number)")
            if not self.closed_date:
                issues.append(f"Item is done, missing closed date, suggest {datetime.datetime.now()}")

        # TODO: check for mandatory fields <matth 2025-07-04 assignee:matth status:done category:validation
        #  release:0.3.0 closed_date:2025-07-05 change_type:Added>
        mandatory_fields = config.mandatory_fields()
        skip_if_closed = ["priority", "iteration"]
        if mandatory_fields:
            for mandatory_field in mandatory_fields:
                if mandatory_field in skip_if_closed and self.is_probably_done():
                    continue
                if not getattr(self, mandatory_field):
                    suggestions = []
                    if mandatory_field == "status":
                        suggestions = config.valid_status()
                    elif mandatory_field == "category":
                        suggestions = config.valid_categories()
                    elif mandatory_field == "priority":
                        suggestions = config.valid_priorities()
                    elif mandatory_field == "iteration":
                        suggestions = config.valid_iterations()

                    if suggestions:
                        issues.append(f"{mandatory_field} is required, suggest {suggestions}")
                    else:
                        issues.append(f"{mandatory_field} is required")

        # Authors from config.
        # TODO: Implement authors from files
        #  <matth 2025-07-04 status:development category:validation priority:high release:2.0.0 iteration:1>
        authors_list = config.valid_authors()
        if authors_list:
            for person in (self.originator, self.assignee):
                if isinstance(person, list):
                    for subperson in person:
                        if subperson.lower() not in authors_list:
                            issues.append(f"Person '{subperson}' is not on the valid authors list, {authors_list}")
                elif isinstance(person, str) and person.lower() not in authors_list:
                    issues.append(f"Person '{person}' is not on the valid authors list, {authors_list}")

        # TODO: Implement release/version from files
        #  <matth 2025-07-04 status:development category:parser priority:medium release:2.0.0 iteration:1>
        release_list = config.valid_releases()
        if release_list:
            if self.release and self.release not in release_list:
                issues.append(f"Release '{self.release}' is not on the valid release list {release_list}")

        # TODO: Implement release/version from files <matth 2025-07-04
        #  priority:low category:validation status:development release:2.0.0 iteration:1>

        valid_change_list = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
        if self.is_probably_done():
            if (self.change_type or "").lower().strip() not in [_.lower() for _ in valid_change_list]:
                issues.append(f"change_type '{self.change_type}' is not on the valid list {valid_change_list}")

        # Zero business logic checks

        valid_lists_meta = {
            "status": config.valid_status,
            "priority": config.valid_priorities,
            "iteration": config.valid_iterations,
            "category": config.valid_categories,
        }

        for valid_field, valid_list_func in valid_lists_meta.items():
            valid_list = valid_list_func()
            if valid_list:
                value = getattr(self, valid_field)
                if value is None:
                    value = ""
                if value.lower() not in valid_list + [""]:
                    issues.append(f"Invalid {valid_field} {value}, valid {valid_field} {valid_list}")

        custom_fields_list = config.valid_custom_field_names()
        if custom_fields_list:
            if self.custom_fields:
                for custom_field in self.custom_fields:
                    if custom_field.lower() not in custom_fields_list:
                        issues.append(
                            f"Custom field '{custom_field}' is not on the valid custom field list {custom_fields_list}"
                        )

        # Plugin-based validation
        plugin_issues: list[str] = []

        # pylint: disable=import-outside-toplevel
        from pycodetags.plugin_manager import get_plugin_manager

        for new_issues in get_plugin_manager().hook.validate(item=self, config=get_code_tags_config()):
            plugin_issues += new_issues
            issues.extend(plugin_issues)

        return issues

    def as_pep350_comment(self) -> str:
        """Print as if it was a PEP-350 comment.
        Upgrades folk schema to PEP-350
        """
        # self._extract_data_fields()

        # default fields
        if self.default_fields is None:
            self.default_fields = {}

        if self.data_fields is None:
            self.data_fields = {}
        if self.custom_fields is None:
            self.custom_fields = {}

        for _, name in IssueTrackerSchema["default_fields"].items():
            value = getattr(self, name)
            if value is not None:
                self.default_fields[name] = value

        # data_fields
        for name in TODO_KEYWORDS:
            value = getattr(self, name)
            if value is not None:
                self.data_fields[name] = value

        return self.as_data_comment()
