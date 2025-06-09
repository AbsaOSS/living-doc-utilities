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
This module contains the IssueFactory class, which dynamically creates instances of Issue subclasses based
 on their class name.
"""

from typing import Any

from living_doc_utilities.model.issue import Issue
from living_doc_utilities.model.user_story_issue import UserStoryIssue
from living_doc_utilities.model.feature_issue import FeatureIssue
from living_doc_utilities.model.functionality_issue import FunctionalityIssue


class IssueFactory:
    """
    Factory class that dynamically instantiates Issue subclasses by name.

    If the given type is not found, it falls back to the base Issue class.
    """

    @classmethod
    def get(cls, class_name: str, values: dict[str, Any]) -> "Issue":
        """
        Return an instance of the Issue subclass by name.

        @param class_name: The name of the Issue class to instantiate.
        @param values: A dictionary of values to initialize the Issue instance.

        @return: An instance of the matched Issue subclass, or base Issue.
        """
        match class_name:
            case "UserStoryIssue":
                return UserStoryIssue.from_dict(values)
            case "FeatureIssue":
                return FeatureIssue.from_dict(values)
            case "FunctionalityIssue":
                return FunctionalityIssue.from_dict(values)
            case _:
                return Issue.from_dict(values)
