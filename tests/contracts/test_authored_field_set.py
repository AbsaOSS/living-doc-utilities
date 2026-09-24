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
"""Every authored heading/key the contract models must carry a field for."""

import pytest

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.common import AcceptanceCriterion
from living_doc_utilities.contracts.doc_entities import Entity

# (heading/key, owning model, field name), following living-doc's tools/examples_check.py.
USER_STORY_HEADINGS = [
    ("Description", Entity, "narrative"),
    ("Status", Entity, "state"),
    ("Business Value", Entity, "business_value"),
    ("Acceptance Criteria", Entity, "acceptance_criteria"),
    ("Preconditions", Entity, "preconditions"),
    ("Not In Scope", Entity, "not_in_scope"),
    ("Deprecated At", Entity, "deprecated_at"),
    ("Deprecation Reason", Entity, "deprecation_reason"),
    ("Superseded By", Entity, "superseded_by"),
]

# Feature carries no "Status" heading - its state is derived (see test_doc_entities.py).
FEATURE_HEADINGS = [
    ("Description", Entity, "purpose"),
    ("Surface Type", Entity, "surface_type"),
    ("Owners", Entity, "owners"),
    ("User Stories", Entity, "user_stories"),
    ("Functionalities", Entity, "functionalities"),
    ("External Dependencies", Entity, "external_dependencies"),
    ("Deprecated At", Entity, "deprecated_at"),
    ("Deprecation Reason", Entity, "deprecation_reason"),
    ("Superseded By", Entity, "superseded_by"),
]

FUNCTIONALITY_HEADINGS = [
    ("Description", Entity, "narrative"),
    ("Status", Entity, "state"),
    ("Parent Feature", Entity, "parent"),
    ("Func Type", Entity, "func_type"),
    ("Acceptance Criteria", Entity, "acceptance_criteria"),
    ("Rationale", Entity, "rationale"),
    ("Preconditions", Entity, "preconditions"),
    ("Not In Scope", Entity, "not_in_scope"),
    ("Deprecated At", Entity, "deprecated_at"),
    ("Deprecation Reason", Entity, "deprecation_reason"),
    ("Superseded By", Entity, "superseded_by"),
]

# The .feature-header keys describe the entity the file documents; only "source" has no field from ISSUE_HEADINGS.
FEATURE_FILE_HEADER_OPTIONAL_KEYS = [
    ("source", Entity, "source"),
    ("rationale", Entity, "rationale"),
    ("preconditions", Entity, "preconditions"),
    ("not_in_scope", Entity, "not_in_scope"),
    ("deprecated_at", Entity, "deprecated_at"),
    ("deprecation_reason", Entity, "deprecation_reason"),
    ("superseded_by", Entity, "superseded_by"),
]

PAGE_OBJECT_OPTIONAL_KEYS = [
    ("wizard-steps", Entity, "wizard_steps"),
    ("stub-reason", Entity, "stub_reason"),
]

AC_BLOCK_EXTENSIONS = [
    ("aspect", AcceptanceCriterion, "aspect"),
    ("preconditions", AcceptanceCriterion, "preconditions"),
    ("not-in-scope", AcceptanceCriterion, "not_in_scope"),
    ("rationale", AcceptanceCriterion, "rationale"),
    ("placeholder values", AcceptanceCriterion, "placeholder_values"),
]

ALL_HEADINGS = (
    USER_STORY_HEADINGS
    + FEATURE_HEADINGS
    + FUNCTIONALITY_HEADINGS
    + FEATURE_FILE_HEADER_OPTIONAL_KEYS
    + PAGE_OBJECT_OPTIONAL_KEYS
    + AC_BLOCK_EXTENSIONS
)


_IDS = [f"{model.__name__}.{field_name}" for _, model, field_name in ALL_HEADINGS]


@pytest.mark.parametrize("heading, model, field_name", ALL_HEADINGS, ids=_IDS)
def test_authored_heading_has_a_field_on_the_shared_model(heading, model, field_name):
    """Every authored heading in the table maps to a real field on its shared pydantic model."""
    assert field_name in model.model_fields, f"heading '{heading}' has no '{field_name}' field on {model.__name__}"


def test_every_heading_in_this_table_is_exercised():
    """The heading table's combined length matches the expected count, so no list silently went empty."""
    # Guards the table: an emptied list would make the parametrized test silently stop covering it.
    assert len(ALL_HEADINGS) == 9 + 9 + 11 + 7 + 2 + 5


def test_parsed_entity_field_set_equals_entity_minus_provenance_by_construction():
    """`ParsedEntity`'s field set equals `Entity`'s minus the provenance-only fields, by shared-base construction."""
    # Both derive their authored fields from the shared EntityContent base, so this holds structurally.
    assert set(ParsedEntity.model_fields) == set(Entity.model_fields) - {"source_ref", "tags", "timestamps"}
