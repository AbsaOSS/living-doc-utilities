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
from living_doc_utilities.model.functionality_issue import FunctionalityIssue


def test_get_related_feature_ids_no_body():
    issue = FunctionalityIssue()
    issue.body = None
    assert issue.get_related_feature_ids() == []

def test_get_related_feature_ids_no_section():
    issue = FunctionalityIssue()
    issue.body = "Some unrelated text\n- #42"
    assert issue.get_related_feature_ids() == []

def test_get_related_feature_ids_with_features():
    issue = FunctionalityIssue()
    issue.body = (
        "### Associated Feature\n"
        "- #13\n"
        "- #14\n"
        "Other text"
    )
    assert issue.get_related_feature_ids() == [13, 14]

def test_get_related_feature_ids_mixed_content():
    issue = FunctionalityIssue()
    issue.body = (
        "Intro\n"
        "### Associated Feature\n"
        "- #101\n"
        "- #202\n"
        "\n### Something else\n"
        "- #303"
    )
    assert issue.get_related_feature_ids() == [101, 202]
