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
The one-line fix hint the check's report puts after each finding: one per code of the default fail list, and one for
a missing feature-level tag.
"""

FIX_HINTS: dict[str, str] = {
    "AUTHORING_ERROR": "Keep the line inside the header, with its comment marker, under the key it belongs to.",
    "AUTHORING_WARNING": "Put the line under the field it belongs to, or remove it: nothing reads it.",
    "FEATURE_WITHOUT_FUNCTIONALITY": "Link a Functionality to the Feature with its 'parent:', or remove the Feature.",
    "HTML_CONTENT_DROPPED": "Write the content as Markdown: the converter drops this HTML.",
    "IGNORED_AUTHORED_KEY": "Remove the key, or rename it to a key this header carries.",
    "LEGACY_AC_STATE": "Replace the retired state: write 'AC:<id> (planned)', or a version and a current state.",
    "MALFORMED_AC": "Write 'AC:<id> (v<major.minor.patch> - <state>)', or 'AC:<id> (planned)' for a backlog criterion.",
    "MALFORMED_STATUS": "Write one of the values the message lists.",
    "MISINDENTED_LINE": "Indent the line to a level of its list: the template's levels, spaces only.",
    "MISSING_ENTITY_ID": "Open the header with a 'LIVING DOC — <US|FEAT|FUNC>-<nnn> · <name>' title line.",
    "MISSING_REQUIRED_KEY": "Add the key to the header.",
    "MISSING_STATUS": "Add 'status: <state>': planned, in_review, active or deprecated.",
    "RELATION_MISMATCH": "Make both ends agree: the Feature's 'functionalities:' and the Functionality's 'parent:'.",
    "RELATION_TYPE_MISMATCH": "Point the relation at the expected entity type; a dependency must be an API Feature.",
    "STATUS_AC_MISMATCH": "Make 'status:' agree with the states of the entity's own criteria.",
    "UNKNOWN_SECTION": "Rename the heading to one of the layout's '##' headings, or remove it.",
    "UNPARSED_AC_LINE": "Write a description, '- Aspect:', '- Rationale:' or the keyword the text names as '{<name>}'.",
    "UNPARSED_BULLET_LINE": "Start the field's text with a '- ' bullet.",
    "UNRESOLVED_RELATION": "Point the relation at an entity that exists, or restore the entity it names.",
}

# A missing feature-level tag is `MISSING_REQUIRED_KEY` too, but it is fixed above `Feature:`, outside the header.
MISSING_TAG_HINT = "Add the tag above `Feature:`."
