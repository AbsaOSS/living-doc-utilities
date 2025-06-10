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
This module contains the Issue class, which represents the data of an issue.
"""
import logging
from typing import Any, Optional

from living_doc_utilities.model.project_status import ProjectStatus

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Issue:
    """
    Represents an issue in the GitHub repository ecosystem.
    """

    TYPE = "type"
    STATE = "state"
    REPOSITORY_ID = "repository_id"
    TITLE = "title"
    ISSUE_NUMBER = "issue_number"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CLOSED_AT = "closed_at"
    HTML_URL = "html_url"
    BODY = "body"
    LABELS = "labels"
    LINKED_TO_PROJECT = "linked_to_project"
    PROJECT_STATUS = "project_status"

    def __init__(self):
        # issue's properties - required for all issues
        self.repository_id: str = ""
        self.title: str = ""
        self.issue_number: int = 0

        # issue's properties
        self.state: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.closed_at: Optional[str] = None
        self.html_url: Optional[str] = None
        self.body: Optional[str] = None
        self.labels: list[str] = []

        # GitHub Projects related properties
        self.linked_to_project: bool = False
        self.project_statuses: list[ProjectStatus] = []

        # support properties
        self.__errors: dict[str, str] = {}

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the issue into a dictionary representation.

        @return: Dictionary representation of the issue.
        """
        res: dict[str, Any] = {}
        res[self.TYPE] = self.__class__.__name__

        if len(self.repository_id) > 0:
            res[self.REPOSITORY_ID] = self.repository_id
        if len(self.title) > 0:
            res[self.TITLE] = self.title
        if self.issue_number > 0:
            res[self.ISSUE_NUMBER] = self.issue_number

        if self.state:
            res[self.STATE] = self.state
        if self.created_at:
            res[self.CREATED_AT] = self.created_at
        if self.updated_at:
            res[self.UPDATED_AT] = self.updated_at
        if self.closed_at:
            res[self.CLOSED_AT] = self.closed_at
        if self.html_url:
            res[self.HTML_URL] = self.html_url
        if self.body:
            res[self.BODY] = self.body
        if self.labels:
            res[self.LABELS] = self.labels
        if self.project_statuses:
            res[self.PROJECT_STATUS] = [project_status.to_dict() for project_status in self.project_statuses]

        res[self.LINKED_TO_PROJECT] = self.linked_to_project if self.linked_to_project is not None else False

        return res

    @property
    def errors(self) -> dict[str, str]:
        """Getter of the errors that occurred during the issue processing."""
        return self.__errors

    def add_errors(self, errors: dict[str, str]) -> None:
        """
        Setter for the errors that occurred during the issue processing.

        @param value: Dictionary of errors.
        """
        if not isinstance(errors, dict):
            raise TypeError("Errors must be a dictionary.")

        self.__errors.update(errors)

    @property
    def organization_name(self) -> str:
        """
        Extracts the organization name from the repository ID.

        @return: Organization name.
        @raises ValueError: If the repository ID is not in the expected format.
        """
        if self.repository_id is None or "/" not in self.repository_id:
            raise ValueError(f"Invalid repository_id format: {self.repository_id}. Expected format: 'org/repo'")

        parts = self.repository_id.split("/")

        return parts[0]

    @property
    def repository_name(self) -> str:
        """
        Extracts the repository name from the repository ID.

        @return: Repository name.
        @raises ValueError: If the repository ID is not in the expected format.
        """
        if self.repository_id is None or "/" not in self.repository_id:
            raise ValueError(f"Invalid repository_id format: {self.repository_id}. Expected format: 'org/repo'")

        parts = self.repository_id.split("/")

        return parts[1]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Issue":
        """
        Creates an Issue object from a dictionary representation.

        @param data: Dictionary representation of the issue.
        @return: Issue object.
        """
        issue: Issue = cls()

        repository_id = data.get(cls.REPOSITORY_ID, None)
        if repository_id is None:
            logger.error(
                "Not provided repository_id for issue, title: '%s', issue number: %d. Cannot create Issue object.",
                data.get(cls.TITLE, "Unknown"),
                data.get(cls.ISSUE_NUMBER, -1),
            )
            raise ValueError("Repository ID is required to create an Issue object.")
        if not isinstance(repository_id, str):
            raise ValueError("Repository ID must be a string.")
        issue.repository_id = repository_id

        title = data.get(cls.TITLE, None)
        if title is None:
            logger.error("Not provided title for issue, issue number: %d.", data.get(cls.ISSUE_NUMBER, -1))
            raise ValueError("Title is required to create an Issue object.")
        if not isinstance(title, str):
            raise ValueError("Title must be a string.")
        issue.title = title

        issue_number = data.get(cls.ISSUE_NUMBER, None)
        if issue_number is None:
            logger.error(
                "Not provided issue_number for issue, title: '%s'. Cannot create Issue object.",
                data.get(cls.TITLE, "Unknown"),
            )
            raise ValueError("Issue number is required to create an Issue object.")
        if not isinstance(issue_number, int):
            raise ValueError("Issue number must be an integer.")
        if issue_number <= 0:
            logger.error(
                "Provided issue_number for issue, title: '%s', is not a positive integer: %d. "
                "Cannot create Issue object.",
                data.get(cls.TITLE, "Unknown"),
                issue_number,
            )
            raise ValueError("Issue number must be a positive integer.")
        issue.issue_number = issue_number

        issue.state = data.get(cls.STATE, None)
        issue.created_at = data.get(cls.CREATED_AT, None)
        issue.updated_at = data.get(cls.UPDATED_AT, None)
        issue.closed_at = data.get(cls.CLOSED_AT, None)
        issue.html_url = data.get(cls.HTML_URL, None)
        issue.body = data.get(cls.BODY, None)
        issue.labels = data.get(cls.LABELS, [])
        issue.linked_to_project = data.get(cls.LINKED_TO_PROJECT, False)

        project_statuses_data = data.get(cls.PROJECT_STATUS, None)
        if project_statuses_data and isinstance(project_statuses_data, list):
            issue.project_statuses = [ProjectStatus.from_dict(status_data) for status_data in project_statuses_data]
        else:
            issue.project_statuses = []

        return issue

    def is_valid_issue(self) -> bool:
        """
        Validates the issue data.

        @return: True if the issue is valid, False otherwise.
        """
        return all([self.repository_id, self.title, self.issue_number > 0])
