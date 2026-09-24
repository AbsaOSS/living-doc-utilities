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
Every authored heading/key the contract models must carry a field for.

Field set copied from AbsaOSS/living-doc's tools/examples_check.py at commit
bfcc402ff998085cbf7bb91a7fd55ea8ac12c911 ("Docs/24 canon dash states status" and its
follow-up, PRs #25/#26): ISSUE_HEADINGS, DEPRECATION_HEADINGS, OPTIONAL_FEATURE_KEYS and
OPTIONAL_PO_KEYS. See the "Authored field set" section of this repo's issue #128 for the
full per-type breakdown this table reproduces.

Field *names* (as opposed to the headings themselves) follow the same commit's
PAIR_FIELD_MAP and REQUIRED_PO_KEYS_FULL/REQUIRED_PO_KEYS_XREF - e.g. "Description" pairs
with `narrative` for a User Story/Functionality and `purpose` for a Feature, "Parent
Feature" pairs with `parent`, "User Stories"/"Functionalities" are unprefixed lists of ids.
"""

import pytest

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.common import AcceptanceCriterion
from living_doc_utilities.contracts.doc_entities import Entity

# (heading/key, owning model, field name)
# Description pairs with a different key per type (living-doc's PAIR_FIELD_MAP): `narrative`
# for a User Story or Functionality, `purpose` for a Feature (its PageObject header's key).
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

# These key the User Story / Functionality .feature header (living-doc's
# corpus.declare_form(entity_id, "feature-file header", ...)) - they describe the entity the
# file documents, not an individual scenario in it. All but "source" already have a field
# from ISSUE_HEADINGS above; only "source" (a pointer back to this entity's issue-tracker
# counterpart) is new.
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
    assert field_name in model.model_fields, f"heading '{heading}' has no '{field_name}' field on {model.__name__}"


def test_every_heading_in_this_table_is_exercised():
    # Guards the table itself: if a future edit empties one of the lists above, the
    # parametrized test would just silently stop covering it.
    assert len(ALL_HEADINGS) == 9 + 9 + 11 + 7 + 2 + 5


def test_parsed_entity_field_set_equals_entity_minus_provenance_by_construction():
    # Both derive their authored fields from the one shared EntityContent base, so this
    # holds structurally - not from two hand-kept lists (S-11/Q-04).
    assert set(ParsedEntity.model_fields) == set(Entity.model_fields) - {"source_ref", "tags", "timestamps"}
