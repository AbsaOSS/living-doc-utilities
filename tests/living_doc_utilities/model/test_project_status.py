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
from src.living_doc_utilities.constants import NO_PROJECT_DATA
from src.living_doc_utilities.model.project_status import ProjectStatus


def test_project_status_initialization():
    # Arrange & Act
    project_status = ProjectStatus()

    # Assert
    assert project_status.project_title == NO_PROJECT_DATA
    assert project_status.status == NO_PROJECT_DATA
    assert project_status.priority == NO_PROJECT_DATA
    assert project_status.size == NO_PROJECT_DATA
    assert project_status.moscow == NO_PROJECT_DATA


def test_project_status_setters_and_getters():
    # Arrange
    project_status = ProjectStatus()

    # Act
    project_status.project_title = "Test Project"
    project_status.status = "In Progress"
    project_status.priority = "High"
    project_status.size = "Large"
    project_status.moscow = "Must Have"

    # Assert
    assert project_status.project_title == "Test Project"
    assert project_status.status == "In Progress"
    assert project_status.priority == "High"
    assert project_status.size == "Large"
    assert project_status.moscow == "Must Have"


def test_project_status_to_dict():
    # Arrange
    project_status = ProjectStatus()
    project_status.project_title = "Test Project"
    project_status.status = "In Progress"
    project_status.priority = "High"
    project_status.size = "Large"
    project_status.moscow = "Must Have"

    # Act
    result = project_status.to_dict()

    # Assert
    assert result == {
        "project_title": "Test Project",
        "status": "In Progress",
        "priority": "High",
        "size": "Large",
        "moscow": "Must Have",
    }


def test_project_status_from_dict():
    # Arrange
    data = {
        "project_title": "Test Project",
        "status": "In Progress",
        "priority": "High",
        "size": "Large",
        "moscow": "Must Have",
    }

    # Act
    project_status = ProjectStatus.from_dict(data)

    # Assert
    assert project_status.project_title == "Test Project"
    assert project_status.status == "In Progress"
    assert project_status.priority == "High"
    assert project_status.size == "Large"
    assert project_status.moscow == "Must Have"


def test_project_status_from_dict_with_missing_fields():
    # Arrange
    data = {"project_title": "Test Project"}

    # Act
    project_status = ProjectStatus.from_dict(data)

    # Assert
    assert project_status.project_title == "Test Project"
    assert project_status.status == NO_PROJECT_DATA
    assert project_status.priority == NO_PROJECT_DATA
    assert project_status.size == NO_PROJECT_DATA
    assert project_status.moscow == NO_PROJECT_DATA
