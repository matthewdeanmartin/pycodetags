from __future__ import annotations

from pycodetags_issue_tracker.user import get_current_user
from pycodetags_issue_tracker.users_from_authors import parse_authors_file_simple

from pycodetags.config import CodeTagsConfig, careful_to_bool, get_code_tags_config


class IssueTrackerConfig:
    def __init__(self, parent_config: CodeTagsConfig, set_user: str | None = None):

        self.parent_config = parent_config
        self.user_override = set_user

    def user_env_var(self) -> str:
        """Environment variable with active user."""
        return str(self.parent_config.config.get("user_env_var", ""))

    def current_user(self) -> str:
        if self.user_override:
            return self.user_override
        return get_current_user(self.user_identification_technique(), self.user_env_var())

    def user_identification_technique(self) -> str:
        """Technique for identifying current user. If not set, related features are disabled."""
        field = "user_identification_technique"
        result = self.parent_config.config.get(field, "")
        accepted = ("os", "env", "git", "")
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def valid_authors_file(self) -> str:
        """Author list, overrides valid authors if specified. File must exist."""
        field = "valid_authors_file"
        return str(self.parent_config.config.get(field, ""))

    def valid_authors_schema(self) -> str:
        """Author schema, must be specified if authors from file is set."""
        field = "valid_authors_schema"
        result = self.parent_config.config.get(field, "")
        accepted = ("gnu_gnits", "single_column", "")
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        if self.valid_authors_file() and result == "":
            raise TypeError(
                "Invalid configuration: if valid_authors_from_file is set, "
                f"then must be valid_authors_schema must be set to one of {accepted}"
            )
        return str(self.parent_config.config.get("valid_authors_schema", ""))

    # Property accessors
    def valid_authors(self) -> list[str]:
        """Author list, if empty or None, all are valid, unless file specified"""
        author_file = self.valid_authors_file()
        schema = self.valid_authors_schema()
        if author_file and schema:
            if schema == "single_column":
                with open(author_file, encoding="utf-8") as file_handle:
                    authors = [_ for _ in file_handle.readlines() if _]
                return authors
            if schema == "gnu_gnits":
                authors = parse_authors_file_simple(author_file)
                return authors

        return [_.lower() for _ in self.parent_config.config.get("valid_authors", [])]

    def valid_releases(self) -> list[str]:
        """Releases (Version numbers), if empty or None, all are valid.
        Past releases that do not match current schema are valid.
        """
        return [str(_).lower() for _ in self.parent_config.config.get("valid_releases", [])]

    def valid_releases_file(self) -> str:
        """File name of file with valid releases"""
        valid_releases_from_file = self.parent_config.config.get("valid_releases_file", "")
        return str(valid_releases_from_file).lower() if valid_releases_from_file else str(valid_releases_from_file)

    def valid_releases_file_schema(self) -> str:
        """Schema used to read from a known file type the valid versions."""
        field = "valid_releases_file_schema"
        result = self.parent_config.config.get(field, "")
        accepted = ("keepachangelog",)
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        if self.valid_releases_file() and not result:
            raise TypeError(f"When valid_releases_from_file is set, {field} must be in {accepted}")
        return str(result)

    def releases_schema(self) -> str:
        """Schema used to parse, sort release (version) numbers.
        Not used to validate anything
        """
        field = "releases_schema"
        result = self.parent_config.config.get(field, "")
        accepted = ("semantic", "pep440", "")
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def valid_priorities(self) -> list[str]:
        """Priority list, if empty or None, all are valid"""
        return [_.lower() for _ in self.parent_config.config.get("valid_priorities", [])]

    def valid_iterations(self) -> list[str]:
        """Iteration list, if empty or None, all are valid."""
        return [_.lower() for _ in self.parent_config.config.get("valid_iterations", [])]

    def valid_custom_field_names(self) -> list[str]:
        """Custom field names, if empty or None, all are valid."""
        return [_.lower() for _ in self.parent_config.config.get("valid_custom_field_names", [])]

    def mandatory_fields(self) -> list[str]:
        """Mandatory fields, if empty or None, no mandatory fields."""
        return [_.lower() for _ in self.parent_config.config.get("mandatory_fields", [])]

    def tracker_domain(self) -> str:
        """Domain of the tracker, used to make ticket links clickable."""
        return str(self.parent_config.config.get("tracker_domain", ""))

    def tracker_style(self) -> str:
        """Style of the tracker, used to make ticket links clickable."""
        field = "tracker_style"
        result = self.parent_config.config.get(field, "")
        accepted = ("url", "ticket", "")
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def valid_status(self) -> list[str]:
        """Status list, if empty or None, all are valid"""
        return [str(_).lower() for _ in self.parent_config.config.get("valid_status", [])]

    def valid_categories(self) -> list[str]:
        """Category list, if empty or None, all are valid"""
        return [str(_).lower() for _ in self.parent_config.config.get("valid_categories", [])]

    def closed_status(self) -> list[str]:
        """If status equals this,then it is closed, needed for business rules"""
        closed_status = self.parent_config.config.get("closed_status", [])
        return [str(_).lower() for _ in closed_status]

    def action_on_past_due(self) -> bool:
        """Do actions do the default action"""
        return careful_to_bool(self.parent_config.config.get("action_on_past_due", False), False)

    def action_only_on_responsible_user(self) -> bool:
        """Do actions do the default action when active user matches"""
        return careful_to_bool(self.parent_config.config.get("action_only_on_responsible_user", False), False)


def get_issue_tracker_config() -> IssueTrackerConfig:
    return IssueTrackerConfig(get_code_tags_config())
