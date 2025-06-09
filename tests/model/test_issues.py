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
import json
import pytest

from living_doc_utilities.model.feature_issue import FeatureIssue
from living_doc_utilities.model.functionality_issue import FunctionalityIssue
from living_doc_utilities.model.issue import Issue
from living_doc_utilities.model.issues import Issues
from living_doc_utilities.model.user_story_issue import UserStoryIssue


def test_issues_initialization():
    # Arrange & Act
    issues = Issues()

    # Assert
    assert issues.issues == {}


def test_add_issue_with_key():
    # Arrange
    issues = Issues()
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1
    key = "org/repo/1"

    # Act
    issues.add_issue(key, issue)

    # Assert
    assert key in issues.issues
    assert issues.issues[key] == issue


def test_get_issue():
    # Arrange
    issues = Issues()
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1
    key = "org/repo/1"
    issues.add_issue(key, issue)

    # Act
    retrieved_issue = issues.get_issue(key)

    # Assert
    assert retrieved_issue == issue


def test_get_issue_key_error():
    issues = Issues()
    missing_key = "org/repo/999"
    with pytest.raises(KeyError) as e:
        issues.get_issue(missing_key)
    assert e.value.args[0] == f"Issue with key '{missing_key}' not found."


def test_all_issues():
    # Arrange
    issues = Issues()
    issue1 = Issue()
    issue1.repository_id = "org/repo"
    issue1.title = "Issue 1"
    issue1.issue_number = 1
    issue2 = Issue()
    issue2.repository_id = "org/repo"
    issue2.title = "Issue 2"
    issue2.issue_number = 2
    issues.add_issue("org/repo1/1", issue1)
    issues.add_issue("org/repo2/2", issue2)

    # Act
    all_issues = issues.all_issues()

    # Assert
    assert len(all_issues) == 2
    assert "org/repo1/1" in all_issues
    assert "org/repo2/2" in all_issues
    assert all_issues["org/repo1/1"] == issue1
    assert all_issues["org/repo2/2"] == issue2


def test_count():
    # Arrange
    issues = Issues()
    issue1 = Issue()
    issue1.repository_id = "org/repo1"
    issue1.title = "Issue 1"
    issue1.issue_number = 1
    issue2 = Issue()
    issue2.repository_id = "org/repo2"
    issue2.title = "Issue 2"
    issue2.issue_number = 2
    issues.add_issue("org/repo1/1", issue1)
    issues.add_issue("org/repo2/2", issue2)

    # Act
    count = issues.count()

    # Assert
    assert count == 2


def test_make_issue_key():
    # Arrange
    organization_name = "org"
    repository_name = "repo"
    issue_number = 1

    # Act
    key = Issues.make_issue_key(organization_name, repository_name, issue_number)

    # Assert
    assert key == "org/repo/1"


def test_save_to_json(tmp_path):
    # Arrange
    issues = Issues()
    issue = Issue()
    issue.repository_id = "org/repo"
    issue.title = "Test Issue"
    issue.issue_number = 1
    key = "org/repo/1"
    issues.add_issue(key, issue)
    file_path = tmp_path / "issues.json"

    # Act
    issues.save_to_json(file_path)

    # Assert
    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()
    assert '"org/repo/1"' in data
    assert '"Test Issue"' in data


def test_load_from_json_no_type(tmp_path):
    # Arrange
    file_path = tmp_path / "issues.json"
    data = {
        "org/repo/1": {
            "repository_id": "org/repo",
            "title": "Test Issue",
            "issue_number": 1,
            "state": "open",
            "created_at": "2025-01-01T00:00:00Z",
            "labels": ["bug"],
            "linked_to_project": True,
            "project_status": [{"project_title": "Test Project"}],
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Act
    issues = Issues.load_from_json(file_path)

    # Assert
    assert len(issues.issues) == 1
    issue = issues.issues["org/repo/1"]
    assert isinstance(issue, Issue)
    assert issue.repository_id == "org/repo"
    assert issue.title == "Test Issue"
    assert issue.issue_number == 1
    assert issue.state == "open"
    assert issue.created_at == "2025-01-01T00:00:00Z"
    assert issue.labels == ["bug"]
    assert issue.linked_to_project is True
    assert len(issue.project_statuses) == 1
    assert issue.project_statuses[0].project_title == "Test Project"


@pytest.mark.parametrize("issue_type,expected_class", [
    ("Issue", Issue),
    ("UserStoryIssue", UserStoryIssue),
    ("FeatureIssue", FeatureIssue),
    ("FunctionalityIssue", FunctionalityIssue),
    ])
def test_load_from_json_specialized_issue_types(tmp_path, issue_type, expected_class):
    # Arrange
    file_path = tmp_path / "issues.json"
    data = {
        "org/repo/1": {
            "repository_id": "org/repo",
            "title": "Test Issue",
            "issue_number": 1,
            "state": "open",
            "created_at": "2025-01-01T00:00:00Z",
            "labels": ["bug"],
            "linked_to_project": True,
            "project_status": [{"project_title": "Test Project"}],
            "type": issue_type,
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Act
    issues = Issues.load_from_json(file_path)

    # Assert
    assert len(issues.issues) == 1
    issue = issues.issues["org/repo/1"]
    assert isinstance(issue, expected_class)
    assert issue.repository_id == "org/repo"
    assert issue.title == "Test Issue"
    assert issue.issue_number == 1
    assert issue.state == "open"
    assert issue.created_at == "2025-01-01T00:00:00Z"
    assert issue.labels == ["bug"]
    assert issue.linked_to_project is True
    assert len(issue.project_statuses) == 1
    assert issue.project_statuses[0].project_title == "Test Project"


def test_load_from_json_file_not_found(mocker):
    mock_logger = mocker.patch("living_doc_utilities.model.issues.logger.warning")
    result = Issues.load_from_json("nonexistent.json")
    assert isinstance(result, Issues)
    assert result.count() == 0
    mock_logger.assert_called_once()
    assert "Issues file not found" in mock_logger.call_args[0][0]


def test_load_from_json_json_decode_error(tmp_path, mocker):
    file_path = tmp_path / "bad.json"
    file_path.write_text("{invalid json")
    mock_logger = mocker.patch("living_doc_utilities.model.issues.logger.error")
    result = Issues.load_from_json(str(file_path))
    assert isinstance(result, Issues)
    assert result.count() == 0
    mock_logger.assert_called_once()
    assert "Failed to parse JSON" in mock_logger.call_args[0][0]


def test_load_from_json_unexpected_exception(mocker):
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("json.load", side_effect=RuntimeError("boom"))
    mock_logger = mocker.patch("living_doc_utilities.model.issues.logger.error")
    result = Issues.load_from_json("anyfile.json")
    assert isinstance(result, Issues)
    assert result.count() == 0
    mock_logger.assert_called_once()
    assert "Unexpected error loading issues" in mock_logger.call_args[0][0]
