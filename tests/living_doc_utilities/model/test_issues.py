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

from src.living_doc_utilities.model.issue import Issue
from src.living_doc_utilities.model.issues import Issues


def test_issues_initialization():
    # Arrange & Act
    issues = Issues()

    # Assert
    assert issues.issues == {}


def test_add_issue_with_key():
    # Arrange
    issues = Issues()
    issue = Issue(repository_id="org/repo", title="Test Issue", number=1)
    key = "org/repo/1"

    # Act
    issues.add_issue(key, issue)

    # Assert
    assert key in issues.issues
    assert issues.issues[key] == issue


def test_get_issue():
    # Arrange
    issues = Issues()
    issue = Issue(repository_id="org/repo", title="Test Issue", number=1)
    key = "org/repo/1"
    issues.add_issue(key, issue)

    # Act
    retrieved_issue = issues.get_issue(key)

    # Assert
    assert retrieved_issue == issue


def test_all_issues():
    # Arrange
    issues = Issues()
    issue1 = Issue(repository_id="org/repo1", title="Issue 1", number=1)
    issue2 = Issue(repository_id="org/repo2", title="Issue 2", number=2)
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
    issue1 = Issue(repository_id="org/repo1", title="Issue 1", number=1)
    issue2 = Issue(repository_id="org/repo2", title="Issue 2", number=2)
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
    issue = Issue(repository_id="org/repo", title="Test Issue", number=1)
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


def test_load_from_json(tmp_path):
    # Arrange
    file_path = tmp_path / "issues.json"
    data = {
        "org/repo/1": {
            "repository_id": "org/repo",
            "title": "Test Issue",
            "number": 1,
            "state": "open",
            "created_at": "2025-01-01T00:00:00Z",
            "labels": ["bug"],
            "linked_to_project": True,
            "project_status": [{"project_title": "Test Project"}],
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        import json
        json.dump(data, f)

    # Act
    issues = Issues.load_from_json(file_path)

    # Assert
    assert len(issues.issues) == 1
    issue = issues.issues["org/repo/1"]
    assert issue.repository_id == "org/repo"
    assert issue.title == "Test Issue"
    assert issue.issue_number == 1
    assert issue.state == "open"
    assert issue.created_at == "2025-01-01T00:00:00Z"
    assert issue.labels == ["bug"]
    assert issue.linked_to_project is True
    assert len(issue.project_statuses) == 1
    assert issue.project_statuses[0].project_title == "Test Project"
