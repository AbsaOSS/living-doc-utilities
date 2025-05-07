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
This module contains a data container for an issue's Project Status.
"""
from living_doc_utilities.constants import NO_PROJECT_DATA


# pylint: disable=too-many-instance-attributes
class ProjectStatus:
    """
    A class representing the project status of an issue is responsible for access
    and change project issue status specifics.
    """

    def __init__(self):
        self.__project_title: str = NO_PROJECT_DATA
        self.__status: str = NO_PROJECT_DATA
        self.__priority: str = NO_PROJECT_DATA
        self.__size: str = NO_PROJECT_DATA
        self.__moscow: str = NO_PROJECT_DATA

    @property
    def project_title(self) -> str:
        """Getter of the issue attached project title."""
        return self.__project_title

    @project_title.setter
    def project_title(self, value: str):
        self.__project_title = value

    @property
    def status(self) -> str:
        """Getter of the issue project status."""
        return self.__status

    @status.setter
    def status(self, value: str):
        self.__status = value

    @property
    def priority(self) -> str:
        """Getter of the issue project priority."""
        return self.__priority

    @priority.setter
    def priority(self, value: str):
        self.__priority = value

    @property
    def size(self) -> str:
        """Getter of the issue project difficulty."""
        return self.__size

    @size.setter
    def size(self, value: str):
        self.__size = value

    @property
    def moscow(self) -> str:
        """Getter of the issue project MoSCoW prioritization."""
        return self.__moscow

    @moscow.setter
    def moscow(self, value: str):
        self.__moscow = value

    def to_dict(self) -> dict:
        """
        Converts the ProjectStatus object to a dictionary.
        """
        return {
            "project_title": self.__project_title,
            "status": self.__status,
            "priority": self.__priority,
            "size": self.__size,
            "moscow": self.__moscow,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectStatus":
        """
        Populates the ProjectStatus object from a dictionary.
        """
        res = ProjectStatus()
        res.project_title = data.get("project_title", NO_PROJECT_DATA)
        res.status = data.get("status", NO_PROJECT_DATA)
        res.priority = data.get("priority", NO_PROJECT_DATA)
        res.size = data.get("size", NO_PROJECT_DATA)
        res.moscow = data.get("moscow", NO_PROJECT_DATA)

        return res
