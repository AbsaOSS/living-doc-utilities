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

from typing import Any, Optional

from living_doc_utilities.model.project_status import ProjectStatus


# pylint: disable=too-many-instance-attributes
class Issue:
    """
    Represents an issue in the GitHub repository ecosystem.
    """

    STATE = "state"
    REPOSITORY_ID = "repository_id"
    TITLE = "title"
    NUMBER = "number"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CLOSED_AT = "closed_at"
    HTML_URL = "html_url"
    BODY = "body"
    LABELS = "labels"
    LINKED_TO_PROJECT = "linked_to_project"
    PROJECT_STATUS = "project_status"

    def __init__(self, repository_id: str, title: str, number: int):
        self.repository_id: str = repository_id
        self.title: str = title
        self.issue_number: int = number

        # issue's properties
        self.state: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.closed_at: Optional[str] = None
        self.html_url: Optional[str] = None
        self.body: Optional[str] = None
        self.labels: Optional[list[str]] = None

        # GitHub Projects related properties
        self.linked_to_project: Optional[bool] = None
        self.project_statuses: Optional[list[ProjectStatus]] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the issue an object to a dictionary representation.

        @return: Dictionary representation of the issue.
        """
        res: dict[str, Any] = {
            "repository_id": self.repository_id,
            "title": self.title,
            "number": self.issue_number,
        }

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

    def organization_name(self) -> str:
        """
        Extracts the organization name from the repository ID.

        @return: Organization name.
        @raises ValueError: If the repository ID is not in the expected format.
        """
        parts = self.repository_id.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid repository_id format: {self.repository_id}. Expected format: 'org/repo'")
        return parts[0]

    def repository_name(self) -> str:
        """
        Extracts the repository name from the repository ID.

        @return: Repository name.
        @raises ValueError: If the repository ID is not in the expected format.
        """
        parts = self.repository_id.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid repository_id format: {self.repository_id}. Expected format: 'org/repo'")
        return parts[1]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Issue":
        """
        Creates an Issue object from a dictionary representation.

        @param data: Dictionary representation of the issue.
        @return: Issue object.
        """
        issue: Issue = cls(
            repository_id=data[cls.REPOSITORY_ID],
            title=data[cls.TITLE],
            number=data[cls.NUMBER],
        )

        issue.state = data.get(cls.STATE, None)
        issue.created_at = data.get(cls.CREATED_AT, None)
        issue.updated_at = data.get(cls.UPDATED_AT, None)
        issue.closed_at = data.get(cls.CLOSED_AT, None)
        issue.html_url = data.get(cls.HTML_URL, None)
        issue.body = data.get(cls.BODY, None)
        issue.labels = data.get(cls.LABELS, None)
        issue.linked_to_project = data.get(cls.LINKED_TO_PROJECT, None)

        project_statuses_data = data.get(cls.PROJECT_STATUS, None)
        if project_statuses_data and isinstance(project_statuses_data, list):
            issue.project_statuses = [ProjectStatus.from_dict(status_data) for status_data in project_statuses_data]
        else:
            issue.project_statuses = None

        return issue
