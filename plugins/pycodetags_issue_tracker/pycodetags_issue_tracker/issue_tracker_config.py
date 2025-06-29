from pycodetags_issue_tracker.user import get_current_user
from pycodetags_issue_tracker.users_from_authors import parse_authors_file_simple

from pycodetags.config import CodeTagsConfig


class IssueTrackerConfig:
    def __init__(self, parent_config:CodeTagsConfig):
        self.parent_config = parent_config

    def current_user(self) -> str:
        if self.user_override:
            return self.user_override
        return get_current_user(self.user_identification_technique(), self.user_env_var())
    def user_identification_technique(self) -> str:
        """Technique for identifying current user. If not set, related features are disabled."""
        field = "user_identification_technique"
        result = self._config.get(field, "")
        accepted = ("os", "env", "git", "")
        if result not in accepted:
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

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

        return [_.lower() for _ in self._config.get("valid_authors", [])]