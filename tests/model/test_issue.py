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
import pytest

from living_doc_utilities.model.issue import Issue
from living_doc_utilities.model.project_status import ProjectStatus


def test_issue_initialization():
    # Arrange & Act
    issue = Issue()

    # Assert
    assert issue.repository_id == ""
    assert issue.title == ""
    assert issue.issue_number == 0
    assert issue.state is None
    assert issue.created_at is None
    assert issue.updated_at is None
    assert issue.closed_at is None
    assert issue.html_url is None
    assert issue.body is None
    assert issue.labels == []
    assert not issue.linked_to_project
    assert issue.project_statuses == []


def test_issue_to_dict():
    # Arrange
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1
    issue.state = "open"
    issue.created_at = "2025-01-01T00:00:00Z"
    issue.updated_at = "2025-02-01T00:00:00Z"
    issue.closed_at = "2025-03-01T00:00:00Z"
    issue.labels = ["bug", "enhancement"]
    issue.linked_to_project = True
    issue.html_url = "url"
    issue.body = "body"
    project_status = ProjectStatus()
    project_status.project_title = "Test Project"
    issue.project_statuses = [project_status]

    # Act
    result = issue.to_dict()

    # Assert
    assert result == {
        "repository_id": "org/repo",
        "title": "Test Issue",
        "issue_number": 1,
        "html_url": "url",
        "body": "body",
        "state": "open",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-02-01T00:00:00Z",
        "closed_at": "2025-03-01T00:00:00Z",
        "labels": ["bug", "enhancement"],
        "linked_to_project": True,
        "project_status": [{"project_title": "Test Project", "status": "---", "priority": "---", "size": "---", "moscow": "---"}],
        "type": "Issue",
    }


def test_issue_from_dict():
    # Arrange
    data = {
        "repository_id": "org/repo",
        "title": "Test Issue",
        "issue_number": 1,
        "state": "open",
        "created_at": "2025-01-01T00:00:00Z",
        "labels": ["bug", "enhancement"],
        "linked_to_project": True,
        "project_status": [{"project_title": "Test Project"}],
    }

    # Act
    issue = Issue.from_dict(data)

    # Assert
    assert issue.repository_id == "org/repo"
    assert issue.title == "Test Issue"
    assert issue.issue_number == 1
    assert issue.state == "open"
    assert issue.created_at == "2025-01-01T00:00:00Z"
    assert issue.labels == ["bug", "enhancement"]
    assert issue.linked_to_project is True
    assert len(issue.project_statuses) == 1
    assert issue.project_statuses[0].project_title == "Test Project"


def test_issue_organization_name():
    # Arrange
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1

    # Act
    org_name = issue.organization_name

    # Assert
    assert org_name == "org"


def test_issue_organization_name_invalid_repository_id():
    issue = Issue()
    issue.repository_id = "invalidformat"
    with pytest.raises(ValueError, match="Invalid repository_id format: invalidformat. Expected format: 'org/repo'"):
        _ = issue.organization_name


def test_issue_repository_name():
    # Arrange
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1

    # Act
    repo_name = issue.repository_name

    # Assert
    assert repo_name == "repo"


@pytest.mark.parametrize("attr", ["organization_name", "repository_name"])
def test_issue_invalid_repository_id_raises_value_error(attr):
    issue = Issue()
    issue.repository_id = "invalidformat"
    with pytest.raises(ValueError, match="Invalid repository_id format: invalidformat. Expected format: 'org/repo'"):
        _ = getattr(issue, attr)


def test_issue_from_dict_project_statuses_none():
    # Arrange
    data = {
        "repository_id": "org/repo",
        "title": "Test Issue",
        "issue_number": 1,
        "state": "open",
        "created_at": "2025-01-01T00:00:00Z",
        # No "project_status" key
    }

    # Act
    issue = Issue.from_dict(data)

    # Assert
    assert issue.project_statuses == []


def test_issue_errors_property_initially_empty():
    issue = Issue()
    assert issue.errors == {}


def test_issue_add_errors_updates_errors():
    issue = Issue()
    errors = {"field1": "error1", "field2": "error2"}
    issue.add_errors(errors)
    assert issue.errors == errors


def test_issue_add_errors_merges_errors():
    issue = Issue()
    issue.add_errors({"field1": "error1"})
    issue.add_errors({"field2": "error2"})
    assert issue.errors == {"field1": "error1", "field2": "error2"}


def test_issue_add_errors_raises_type_error_on_non_dict():
    issue = Issue()
    with pytest.raises(TypeError):
        issue.add_errors(["not", "a", "dict"])


def test_issue_is_valid_issue_all_fields_present():
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test"
    issue.issue_number = 1
    assert issue.is_valid_issue()


def test_issue_is_not_valid_issue_missing_repository_id():
    issue = Issue()
    issue.title = "Test"
    issue.issue_number = 1
    assert not issue.is_valid_issue()


def test_issue_is_valid_issue_missing_title():
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.issue_number = 1
    assert issue.is_valid_issue() is False


def test_issue_is_valid_issue_missing_issue_number():
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test"
