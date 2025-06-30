"""
A module for calculating health metrics based on TODO items.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pycodetags_issue_tracker.todo_tag_types import TODO


class HealthOMeter:
    """
    Calculates various health metrics from a list of TODO items.

    This class operates solely on the provided TODO objects and has no
    dependencies on file systems or reporting mechanisms.
    """

    # Define sentiment scores for specific code tags
    SENTIMENT_SCORES_PER_TAG = {
        "CLEVER": 2,  # Very positive
        "MAGIC": 1,  # Positive
        "HACK": -1,  # Negative
        "FIXME": -2,  # More negative
        "BUG": -3,  # Most negative
    }

    def __init__(self, todos: list[TODO]) -> None:
        """
        Initializes the HealthOMeter with a list of TODO items.

        Args:
            todos: A list of TODO objects to analyze.
        """
        self.todos = todos
        # Cache the total number of TODOs to avoid repeated recalculations
        self.total_todos_count = len(todos)

    def calculate_todos_per_file(self) -> dict[str, int]:
        """
        Calculates the count of TODOs for each file.

        TODO: Consider a metric for average TODOs per file.
        TODO: Add a metric for files with no TODOs, but high complexity.

        Returns:
            A dictionary mapping file paths to the count of TODOs in them.
        """
        todos_per_file: dict[str, int] = defaultdict(int)
        for todo in self.todos:
            if todo._file_path:
                todos_per_file[todo._file_path] += 1
        return dict(todos_per_file)

    def calculate_total_dones(self) -> int:
        """
        Calculates the total count of TODOs marked as "done".

        TODO: Add a metric for the rate of DONE items over time.

        Returns:
            The total count of TODOs marked as "done".
        """
        return sum(1 for todo in self.todos if todo.is_probably_done())

    def calculate_total_todos(self) -> int:
        """
        Calculates the total count of all TODO items.

        TODO: Add a metric for the trend of total TODOs over time (increasing/decreasing).

        Returns:
            The total count of all TODOs.
        """
        return self.total_todos_count

    def calculate_sentiment_score(self) -> float:
        """
        Calculates a sentiment score based on the presence of specific tags
        (CLEVER, MAGIC, HACK, FIXME, BUG). A higher score indicates better sentiment.

        TODO: Allow configuration of which tags influence sentiment and their scores.

        Returns:
            A score normalized between 0.0 and 1.0. Returns 1.0 if no TODOs exist.
        """
        if self.total_todos_count == 0:
            return 1.0

        raw_sentiment_sum = 0
        for todo in self.todos:
            # Check if the code_tag exists and is in our sentiment mapping
            if todo.code_tag and todo.code_tag.upper() in self.SENTIMENT_SCORES_PER_TAG:
                raw_sentiment_sum += self.SENTIMENT_SCORES_PER_TAG[todo.code_tag.upper()]

        # Determine the min and max possible sentiment sums for normalization
        max_score_per_todo = max(self.SENTIMENT_SCORES_PER_TAG.values())
        min_score_per_todo = min(self.SENTIMENT_SCORES_PER_TAG.values())

        min_possible_total = self.total_todos_count * min_score_per_todo
        max_possible_total = self.total_todos_count * max_score_per_todo

        # Normalize the raw sum to a 0-1 scale: (actual - min_possible) / (max_possible - min_possible)
        if max_possible_total == min_possible_total:
            # Avoid division by zero if all scores are identical or there are no relevant tags
            return 1.0  # Represents a neutral or ideal state in such cases

        normalized_score = (raw_sentiment_sum - min_possible_total) / (max_possible_total - min_possible_total)

        # Ensure the score stays within the [0, 1] range due to potential edge cases or non-linear distribution
        return max(0.0, min(1.0, normalized_score))

    def calculate_quality_score(self) -> float:
        """
        Calculates a quality score based on the presence of "BUG" tags.
        A higher score indicates better quality (fewer BUGs).

        Returns:
            A score normalized between 0.0 and 1.0. Returns 1.0 if no TODOs exist.
        """
        if self.total_todos_count == 0:
            return 1.0

        total_bugs = sum(1 for todo in self.todos if todo.code_tag and todo.code_tag.upper() == "BUG")
        # Quality decreases with more bugs. Scale from 1.0 (no bugs) to 0.0 (all todos are bugs, worst case).
        return max(0.0, (self.total_todos_count - total_bugs) / self.total_todos_count)

    def calculate_bug_density(self) -> float:
        """
        Calculates the density of BUG tags as the ratio of BUGs to total TODOs.
        This serves as a proxy for 'bugs per line of code/function' given
        the class's constraint of not accessing the file system directly.

        TODO: Enhance this metric by allowing external provision of actual
              Lines of Code (LoC) or function counts per file to get a true density.

        Returns:
            The ratio of BUGs to total TODOs (0.0 if no TODOs).
        """
        if self.total_todos_count == 0:
            return 0.0  # No bugs if no todos

        total_bugs = sum(1 for todo in self.todos if todo.code_tag and todo.code_tag.upper() == "BUG")
        return total_bugs / self.total_todos_count

    def get_total_todos_scale(self, total_todos_value: int) -> str:
        """Provides a descriptive scale for the total number of TODOs."""
        if total_todos_value == 0:
            return "Immaculate Codebase"
        elif 1 <= total_todos_value <= 10:
            return "Well-Maintained"
        elif 11 <= total_todos_value <= 50:
            return "Active Development"
        elif 51 <= total_todos_value <= 100:
            return "Busy Beaver"
        else:  # > 100
            return "Technical Debt Accumulation"

    def get_sentiment_scale(self, sentiment_score_value: float) -> str:
        """Provides a descriptive scale for the sentiment score."""
        if 0.8 <= sentiment_score_value <= 1.0:
            return "Positive Outlook"
        elif 0.5 <= sentiment_score_value < 0.8:
            return "Mixed Feelings"
        elif 0.2 <= sentiment_score_value < 0.5:
            return "Caution Advised"
        else:  # 0.0 <= score < 0.2
            return "Coding Horror"

    def get_quality_scale(self, quality_score_value: float) -> str:
        """Provides a descriptive scale for the code quality score."""
        if 0.95 <= quality_score_value <= 1.0:
            return "High Quality"
        elif 0.8 <= quality_score_value < 0.95:
            return "Good Quality"
        elif 0.5 <= quality_score_value < 0.8:
            return "Average Quality"
        else:  # 0.0 <= score < 0.5
            return "Buggy Waters"

    def get_bug_density_scale(self, bug_density_value: float) -> str:
        """Provides a descriptive scale for the bug density."""
        if 0.0 == bug_density_value:
            return "Bug-Free Zone"
        elif 0.0 < bug_density_value <= 0.05:
            return "Occasional Pests"
        elif 0.05 < bug_density_value <= 0.15:
            return "Frequent Critters"
        else:  # > 0.15
            return "Infestation"

    def calculate_metrics(self) -> dict[str, Any]:
        """
        Calculates and returns a dictionary of all health metrics, including their
        descriptive scales.

        Returns:
            A dictionary containing the calculated metrics and their associated scales.
        """
        total_todos = self.calculate_total_todos()
        sentiment_score = self.calculate_sentiment_score()
        quality_score = self.calculate_quality_score()
        bug_density = self.calculate_bug_density()

        metrics = {
            "todos_per_file": self.calculate_todos_per_file(),
            "total_dones": self.calculate_total_dones(),
            "total_todos": total_todos,
            "sentiment_score": sentiment_score,
            "quality_score": quality_score,
            "bug_density": bug_density,
            "total_todos_scale": self.get_total_todos_scale(total_todos),
            "sentiment_scale": self.get_sentiment_scale(sentiment_score),
            "quality_scale": self.get_quality_scale(quality_score),
            "bug_density_scale": self.get_bug_density_scale(bug_density),
        }

        # Add scale descriptions to the metrics

        return metrics
