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
import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.doc_entities import CONTRACT_ID, RECORD_ROOTS, DocEntitiesResult, Entity, PageRef
from tests.contracts import factories


def test_entity_carries_the_required_identity_and_provenance_fields():
    required = {"entity_id", "state", "state_origin", "source_ref"}

    assert required.issubset(Entity.model_fields)
    assert {"tracker_state", "native_type", "area_path", "iteration_path"}.issubset(
        Entity.model_fields["source_ref"].annotation.model_fields
    )


def test_feature_with_authored_state_origin_fails():
    with pytest.raises(ValidationError, match="state_origin must be 'derived'"):
        factories.feature(state_origin="authored")


def test_user_story_with_stub_reason_fails():
    with pytest.raises(ValidationError, match="stub_reason is only valid on a Feature"):
        factories.user_story(stub_reason="surface not yet instrumented")


def test_functionality_with_stub_reason_fails():
    with pytest.raises(ValidationError, match="stub_reason is only valid on a Feature"):
        factories.functionality(stub_reason="surface not yet instrumented")


def test_user_story_with_derived_state_origin_fails():
    with pytest.raises(ValidationError, match="state_origin must be 'authored'"):
        factories.user_story(state_origin="derived")


def test_functionality_with_derived_state_origin_fails():
    with pytest.raises(ValidationError, match="state_origin must be 'authored'"):
        factories.functionality(state_origin="derived")


def test_feature_with_derived_state_origin_and_stub_reason_is_valid():
    result = factories.feature(state_origin="derived", stub_reason="surface not yet instrumented")

    assert result.state_origin == "derived"
    assert result.stub_reason == "surface not yet instrumented"


def test_feature_without_stub_reason_is_valid():
    result = factories.feature()

    assert result.stub_reason is None


def test_github_shaped_entity_validates():
    result = factories.user_story(source_ref=factories.github_source_ref())

    assert result.source_ref.system == "GitHub"


def test_azure_devops_shaped_entity_validates():
    result = factories.functionality(source_ref=factories.azure_devops_source_ref())

    assert result.source_ref.system == "AzureDevOps"
    assert result.source_ref.area_path is not None


def test_entity_forbids_unknown_field():
    with pytest.raises(ValidationError):
        factories.user_story(not_a_real_field="nope")


def test_acceptance_criterion_id_must_belong_to_its_entity():
    mismatched_ac = factories.acceptance_criterion(parent_id="US-999")
    with pytest.raises(ValidationError, match="does not belong to entity 'US-001'"):
        factories.user_story(entity_id="US-001", acceptance_criteria=[mismatched_ac])


def test_acceptance_criterion_id_matching_its_entity_is_valid():
    result = factories.functionality(entity_id="FUNC-042")

    assert result.acceptance_criteria[0].id == "FUNC-042-01"


def test_feature_purpose_is_separate_from_user_story_narrative():
    story = factories.user_story()
    surface = factories.feature()

    assert story.narrative is not None and story.purpose is None
    assert surface.purpose is not None and surface.narrative is None


def test_feature_pages_carries_the_primary_and_cross_reference_page_objects():
    primary = factories.page_ref(is_primary=True, route="/checkout", page_object="CheckoutPage.ts")
    step = factories.page_ref(
        is_primary=False, route="/checkout/shipping", page_object="CheckoutShippingPage.ts", functionalities=["FUNC-002"]
    )
    result = factories.feature(pages=[primary, step])

    assert [p.page_object for p in result.pages] == ["CheckoutPage.ts", "CheckoutShippingPage.ts"]
    assert result.pages[1].functionalities == ["FUNC-002"]


def test_page_ref_forbids_unknown_field():
    with pytest.raises(ValidationError):
        PageRef(route="/x", page_object="X.ts", purpose="...", not_a_real_field="nope")


def test_entity_type_enum_has_the_three_documentation_types():
    schema = Entity.model_json_schema()

    assert schema["properties"]["type"]["enum"] == [
        "DocumentedUserStory",
        "DocumentedFeature",
        "DocumentedFunctionality",
    ]


def test_doc_entities_result_uses_entities_array_key():
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[factories.user_story()])

    assert len(result.entities) == 1
    assert "items" not in DocEntitiesResult.model_fields


def test_doc_entities_result_schema_version_is_the_contract_id():
    result = DocEntitiesResult(metadata=factories.metadata())

    assert result.schema_version == CONTRACT_ID == "doc-entities-v1.0.0"


def test_record_roots_declares_entities():
    assert RECORD_ROOTS == {"entities": Entity}
