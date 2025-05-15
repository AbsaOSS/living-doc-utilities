#
# Copyright 2025 ABSA Group Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This module contains the Issues class, which is used to manage issues in the GitHub repository ecosystem.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from living_doc_utilities.model.issue import Issue

logger = logging.getLogger(__name__)


class Issues:
    """
    This class represents a collection of issues in a GitHub repository ecosystem.
    """

    def __init__(self, issues: Optional[dict[str, Issue]] = None) -> None:
        self.issues: dict[str, Issue] = issues or {}

    def save_to_json(self, file_path: str | Path) -> None:
        """
        Save the issues to a JSON file.

        @param file_path: Path to the JSON file.
        @return: None
        """
        data = {key: ci.to_dict() for key, ci in self.issues.items()}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # pylint: disable=broad-exception-caught
    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "Issues":
        """
        Load issues from a JSON file.

        @param file_path: Path to the JSON file.
        @return: Issues object.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            issues = {key: Issue.from_dict(value) for key, value in data.items()}
            return cls(issues)
        except FileNotFoundError:
            logger.warning("Issues file not found at %s. Returning empty Issues object.", file_path)
            return cls()
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from %s. Returning empty Issues object.", file_path)
            return cls()
        except Exception as e:
            logger.error("Unexpected error loading issues from %s: %s", file_path, str(e))
            return cls()

    def add_issue(self, key: str, issue: Issue) -> None:
        self.issues[key] = issue

    def get_issue(self, key: str) -> Issue:
        try:
            return self.issues[key]
        except KeyError:
            raise KeyError(f"Issue with key '{key}' not found") from None

    def all_issues(self) -> dict[str, Issue]:
        return self.issues

    def count(self) -> int:
        return len(self.issues)

    @staticmethod
    def make_issue_key(organization_name: str, repository_name: str, issue_number: int) -> str:
        """
        Create a unique string key to identify the issue.

        @param organization_name: The name of the organization where the issue is located at.
        @param repository_name: The name of the repository where the issue is located at.
        @param issue_number: The number of the issue.
        @return: The unique string key for the issue.
        """
        return f"{organization_name}/{repository_name}/{issue_number}"
