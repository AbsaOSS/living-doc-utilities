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
This module defines the FeatureIssue class, which is a specialized type of Issue
"""
import re

from living_doc_utilities.model.issue import Issue


class FunctionalityIssue(Issue):
    """
    Represents a Functionality Issue in the GitHub repository ecosystem.
    It extends the Issue class to include specific methods valid for functionality-type issues.
    """

    def get_related_feature_ids(self) -> list[int]:
        """
        Get the feature IDs from the issue body.

        Expected format:
            ### Associated Feature
            - #13
            - #14

        @return: A list of feature IDs extracted from the issue body.
        """
        if not self.body:
            return []

        pattern = r"### Associated Feature\s*(?:\s*[-*]\s*#\d+)+"
        section_match = re.search(pattern, self.body)
        if not section_match:
            return []

        # Extract just the matched section text
        section_text = section_match.group(0)

        # Find all occurrences of `#<number>` in that section
        id_matches = re.findall(r"#(\d+)", section_text)
        return [int(match) for match in id_matches]
