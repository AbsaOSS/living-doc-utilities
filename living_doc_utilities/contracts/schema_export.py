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
Generates the six contracts' JSON Schemas from their pydantic models (docs/contracts.md,
section 2) and writes them to contracts/schemas/. Run as
`python -m living_doc_utilities.contracts.schema_export`, or `make schemas`.
"""

import json
import logging
from importlib import resources
from pathlib import Path
from types import NoneType
from typing import Any, Iterator, Union, get_args, get_origin

from pydantic import BaseModel

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    ui_test_catalog,
    ui_tests,
)
from living_doc_utilities.contracts.envelope import Stats
from living_doc_utilities.logging_config import setup_logging

logger = logging.getLogger(__name__)

# R1/R2: every exported schema declares its dialect and identifies itself.
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
ID_TEMPLATE = "https://absaoss.github.io/living-doc-utilities/schemas/{contract_id}-schema.json"

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

# Each contract's result model and its declared record roots (docs/contracts.md, section 1).
_CONTRACTS: tuple[tuple[str, type[BaseModel], dict[str, type[BaseModel]]], ...] = (
    (doc_entities.CONTRACT_ID, doc_entities.DocEntitiesResult, doc_entities.RECORD_ROOTS),
    (doc_source.CONTRACT_ID, doc_source.DocSourceResult, doc_source.RECORD_ROOTS),
    (ui_tests.CONTRACT_ID, ui_tests.UITestsResult, ui_tests.RECORD_ROOTS),
    (generator_ready.CONTRACT_ID, generator_ready.GeneratorReadyResult, generator_ready.RECORD_ROOTS),
    (coverage_matrix.CONTRACT_ID, coverage_matrix.CoverageMatrixResult, coverage_matrix.RECORD_ROOTS),
    (ui_test_catalog.CONTRACT_ID, ui_test_catalog.UiTestCatalogResult, ui_test_catalog.RECORD_ROOTS),
)


def _unwrap(annotation: Any) -> tuple[Any, bool]:
    """Peels Optional[...] and list[...] off a field annotation.

    @return: the innermost type, and whether a list level was found.
    """
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(args) == 1:
            return _unwrap(args[0])
        return annotation, False
    if origin is list:
        (item,) = get_args(annotation)
        item_type, _ = _unwrap(item)
        return item_type, True
    return annotation, False


def _iter_leaf_paths(model: type[BaseModel], prefix: str) -> Iterator[str]:
    for field_name, field_info in model.model_fields.items():
        item_type, is_array = _unwrap(field_info.annotation)
        path = f"{prefix}{field_name}[]" if is_array else f"{prefix}{field_name}"
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            yield from _iter_leaf_paths(item_type, f"{path}.")
        else:
            yield path


def field_occupancy_paths(record_roots: dict[str, type[BaseModel]]) -> list[str]:
    """
    Computes the sorted, record-relative leaf paths a contract's own field_occupancy map
    may report (R11): one record root's fields, prefixed by that root and marking every
    array level with "[]".

    @param record_roots: a contract's RECORD_ROOTS declaration.
    @return: the sorted list of leaf paths.
    """
    paths = {
        path
        for root_name, root_model in record_roots.items()
        for path in _iter_leaf_paths(root_model, f"{root_name}[].")
    }
    return sorted(paths)


def _rewrite_pattern_maps(node: Any) -> None:
    """
    Rewrites pydantic's bare `patternProperties` maps into typed `additionalProperties` plus
    `propertyNames: {pattern}` (R9) - pydantic 2.13 emits the former for a pattern-constrained
    dict key and never the latter on its own.
    """
    if isinstance(node, dict):
        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict) and len(pattern_properties) == 1 and "additionalProperties" not in node:
            ((pattern, value_schema),) = pattern_properties.items()
            node["additionalProperties"] = value_schema
            node["propertyNames"] = {"pattern": pattern}
            del node["patternProperties"]
        for value in node.values():
            _rewrite_pattern_maps(value)
    elif isinstance(node, list):
        for item in node:
            _rewrite_pattern_maps(item)


def _inject_own_field_occupancy_enum(schema: dict[str, Any], paths: list[str]) -> None:
    """Constrains a contract's own metadata.stats.field_occupancy keys to its leaf paths (R9)."""
    stats_def = schema.get("$defs", {}).get(Stats.__name__)
    if not isinstance(stats_def, dict):
        raise ValueError(f"expected a '{Stats.__name__}' definition in $defs")
    field_occupancy = stats_def.get("properties", {}).get("field_occupancy")
    if not isinstance(field_occupancy, dict):
        raise ValueError("expected a 'field_occupancy' property on the Stats definition")
    field_occupancy["propertyNames"] = {"enum": paths}


def _inject_cross_field_constraints(schema: dict[str, Any]) -> None:
    """
    Encodes the model_validator cross-field rules pydantic's own model_json_schema() drops
    (AcceptanceCriterion._check_version_required_unless_planned,
    _check_removal_planned_only_when_deprecated; Entity._check_state_origin,
    _check_stub_reason_is_feature_only, _check_pages_have_exactly_one_primary) as `allOf`
    if/then/else so a plain jsonschema validator rejects what pydantic rejects. A no-op for
    a contract whose $defs don't carry that definition (e.g. ui-tests has neither).

    Two model_validator rules are deliberately not encoded here, because plain JSON Schema
    has no keyword that can express them: Entity._check_acceptance_criteria_belong_to_this_entity
    and CoverageMatrixResult._check_acceptance_criteria_belong_to_this_entity both require an
    id field's value to be used as a runtime prefix pattern against a sibling/ancestor
    field's value, which JSON Schema cannot cross-reference. A consumer validating raw JSON
    against the generated schema alone (not through these Pydantic models) will not catch a
    misowned acceptance-criterion id; this is a documented, accepted schema limitation, not
    an oversight - the same is true of GeneratorReadyResult's SelectionSummary entity-total
    identity (see generator_ready.SelectionSummary docstring).
    """
    defs = schema.get("$defs", {})

    acceptance_criterion_def = defs.get("AcceptanceCriterion")
    if isinstance(acceptance_criterion_def, dict):
        acceptance_criterion_def.setdefault("allOf", []).extend(
            [
                {
                    "if": {"properties": {"state": {"const": "planned"}}, "required": ["state"]},
                    "else": {"properties": {"version": {"type": "string"}}, "required": ["version"]},
                },
                {
                    "if": {"properties": {"state": {"const": "deprecated"}}, "required": ["state"]},
                    "then": {"properties": {"removal_planned": {"type": "string"}}, "required": ["removal_planned"]},
                    "else": {"properties": {"removal_planned": {"type": "null"}}},
                },
            ]
        )

    entity_def = defs.get("Entity")
    if isinstance(entity_def, dict):
        entity_def.setdefault("allOf", []).extend(
            [
                {
                    "if": {"properties": {"type": {"const": "DocumentedFeature"}}, "required": ["type"]},
                    "then": {"properties": {"state_origin": {"const": "derived"}}},
                    "else": {"properties": {"state_origin": {"const": "authored"}}},
                },
                {
                    # stub_reason only ever describes a Feature (Entity._check_stub_reason_is_feature_only).
                    "if": {"properties": {"type": {"const": "DocumentedFeature"}}, "required": ["type"]},
                    "else": {"properties": {"stub_reason": {"type": "null"}}},
                },
                {
                    # a non-empty pages list has exactly one primary PageRef
                    # (Entity._check_pages_have_exactly_one_primary).
                    "if": {"properties": {"pages": {"minItems": 1}}},
                    "then": {
                        "properties": {
                            "pages": {
                                "contains": {"properties": {"is_primary": {"const": True}}},
                                "minContains": 1,
                                "maxContains": 1,
                            }
                        }
                    },
                },
            ]
        )


def find_schema_violations(schema: dict[str, Any]) -> list[str]:
    """
    Walks a generated schema for the one rule R9 leaves no exception to: every object is
    either a record (`additionalProperties: false`) or a typed map (`additionalProperties`
    plus `propertyNames`) - never untyped, never a bare `patternProperties`.

    @param schema: a full contract schema document.
    @return: one message per violating node; empty when the schema is clean.
    """
    violations: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                if "properties" in node:
                    if node.get("additionalProperties") is not False:
                        violations.append(f"{path}: record object without additionalProperties: false")
                else:
                    has_typed_map = isinstance(node.get("additionalProperties"), dict) and "propertyNames" in node
                    if "patternProperties" in node or not has_typed_map:
                        violations.append(f"{path}: map without typed additionalProperties + propertyNames")
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(schema, "$")
    return violations


def generate_schema(
    contract_id: str, model: type[BaseModel], record_roots: dict[str, type[BaseModel]]
) -> dict[str, Any]:
    """
    Builds one contract's full JSON Schema: the raw pydantic schema with the R1/R2 header
    keys added and the R9 map post-processing applied.

    @param contract_id: the contract's versioned id, e.g. "doc-entities-v1.0.0".
    @param model: the contract's top-level result model.
    @param record_roots: the contract's RECORD_ROOTS declaration.
    @return: the full schema document, ready to write.
    @raises ValueError: if the generated schema still has an untyped object (R9).
    """
    raw_schema = model.model_json_schema()
    _rewrite_pattern_maps(raw_schema)
    _inject_own_field_occupancy_enum(raw_schema, field_occupancy_paths(record_roots))
    _inject_cross_field_constraints(raw_schema)

    schema: dict[str, Any] = {
        "$schema": SCHEMA_DIALECT,
        "$id": ID_TEMPLATE.format(contract_id=contract_id),
    }
    schema.update(raw_schema)

    violations = find_schema_violations(schema)
    if violations:
        raise ValueError(f"schema for '{contract_id}' has untyped object(s): {violations}")

    return schema


def write_schemas(output_dir: Path = SCHEMAS_DIR) -> list[Path]:
    """
    Regenerates every contract's schema file. Deterministic: re-running without a model
    change produces byte-identical files.

    @param output_dir: the directory to write "<contract-id>-schema.json" files into.
    @return: the written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for contract_id, model, record_roots in _CONTRACTS:
        schema = generate_schema(contract_id, model, record_roots)
        path = output_dir / f"{contract_id}-schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def load_schema(contract_id: str) -> dict[str, Any]:
    """
    Loads one contract's committed schema from the installed package via importlib.resources,
    never from a path relative to the source tree.

    @param contract_id: the contract's versioned id, e.g. "doc-entities-v1.0.0".
    @return: the parsed schema document.
    """
    schema_text = (
        resources.files("living_doc_utilities.contracts") / "schemas" / f"{contract_id}-schema.json"
    ).read_text(encoding="utf-8")
    return json.loads(schema_text)


def main() -> None:
    """Entry point for `python -m living_doc_utilities.contracts.schema_export`."""
    setup_logging()
    for path in write_schemas():
        logger.info("wrote %s", path)


if __name__ == "__main__":
    main()
