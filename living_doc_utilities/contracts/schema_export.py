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
from importlib import resources
from pathlib import Path
from types import NoneType
from typing import Any, Iterator, Union, get_args, get_origin

from pydantic import BaseModel

from living_doc_utilities.contracts import registry
from living_doc_utilities.contracts.envelope import Stats

# R1/R2: every exported schema declares its dialect and identifies itself.
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
ID_TEMPLATE = "https://absaoss.github.io/living-doc-utilities/schemas/{contract_id}-schema.json"

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


def _unwrap(annotation: Any) -> tuple[Any, bool]:
    """Peels Optional[...] and list[...] off a field annotation.

    @return: the innermost type, and whether a list level was found.
    """
    origin = get_origin(annotation)
    if origin is Union:
        (item,) = (arg for arg in get_args(annotation) if arg is not NoneType)
        return _unwrap(item)
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
    schema["$defs"][Stats.__name__]["properties"]["field_occupancy"]["propertyNames"] = {"enum": paths}


# AcCoverage's no-aspects rules share these two building blocks (AcCoverage._check_status_matches_aspects).
_AC_COVERAGE_NO_ASPECTS: dict[str, Any] = {"properties": {"aspects": {"maxItems": 0}}}
_AC_COVERAGE_NOT_COVERED_ASPECT: dict[str, Any] = {
    "properties": {"status": {"const": "not_covered"}},
    "required": ["status"],
}

# Each $defs name's model_validator cross-field rules, encoded as `allOf` if/then/else so a
# plain jsonschema validator rejects what pydantic rejects: AcceptanceCriterion
# (_check_version_required_unless_planned, _check_removal_planned_only_when_deprecated),
# Entity (_check_state_origin, _check_stub_reason_is_feature_only,
# _check_pages_have_exactly_one_primary), AspectCoverage
# (_check_status_matches_scenario_ids), AcCoverage (_check_status_matches_aspects, incl. its
# no-aspects scenario_ids tie-in). A def name absent from a contract's own $defs (e.g.
# ui-tests has neither) is simply skipped by _inject_cross_field_constraints below.
_CROSS_FIELD_RULES: dict[str, list[dict[str, Any]]] = {
    "AcceptanceCriterion": [
        {
            "if": {"properties": {"state": {"const": "planned"}}, "required": ["state"]},
            "else": {"properties": {"version": {"type": "string"}}, "required": ["version"]},
        },
        {
            "if": {"properties": {"state": {"const": "deprecated"}}, "required": ["state"]},
            "then": {"properties": {"removal_planned": {"type": "string"}}, "required": ["removal_planned"]},
            "else": {"properties": {"removal_planned": {"type": "null"}}},
        },
    ],
    "Entity": [
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
                        "contains": {
                            "properties": {"is_primary": {"const": True}},
                            "required": ["is_primary"],
                        },
                        "minContains": 1,
                        "maxContains": 1,
                    }
                }
            },
        },
    ],
    "AspectCoverage": [
        {
            # status is evidence-backed by scenario_ids, never independently authored
            # (AspectCoverage._check_status_matches_scenario_ids).
            "if": {"properties": {"status": {"const": "covered"}}, "required": ["status"]},
            "then": {"properties": {"scenario_ids": {"minItems": 1}}, "required": ["scenario_ids"]},
            "else": {"properties": {"scenario_ids": {"maxItems": 0}}},
        },
    ],
    "AcCoverage": [
        {
            "if": _AC_COVERAGE_NO_ASPECTS,
            "then": {"properties": {"status": {"enum": ["covered", "not_covered"]}}},
        },
        {
            # without aspects, status is evidence-backed by the AC's own scenario_ids (same
            # rule as AspectCoverage, applied at the AC level).
            "if": {
                **_AC_COVERAGE_NO_ASPECTS,
                "properties": {**_AC_COVERAGE_NO_ASPECTS["properties"], "status": {"const": "covered"}},
            },
            "then": {"properties": {"scenario_ids": {"minItems": 1}}, "required": ["scenario_ids"]},
        },
        {
            "if": {
                **_AC_COVERAGE_NO_ASPECTS,
                "properties": {**_AC_COVERAGE_NO_ASPECTS["properties"], "status": {"const": "not_covered"}},
            },
            "then": {"properties": {"scenario_ids": {"maxItems": 0}}},
        },
        {
            "if": {
                "properties": {"aspects": {"minItems": 1}},
                "not": {"properties": {"aspects": {"contains": _AC_COVERAGE_NOT_COVERED_ASPECT}}},
            },
            "then": {"properties": {"status": {"const": "covered"}}},
        },
        {
            "if": {
                "properties": {"aspects": {"minItems": 1, "contains": _AC_COVERAGE_NOT_COVERED_ASPECT}},
                "required": ["aspects"],
            },
            "then": {"properties": {"status": {"const": "partially_covered"}}},
        },
    ],
}


def _inject_cross_field_constraints(schema: dict[str, Any], contract_id: str) -> None:
    """
    Applies _CROSS_FIELD_RULES to `schema`'s $defs, one `allOf` extend per def name that's
    actually present.

    metadata.source_inputs[] additionally gets a `minItems: 1` constraint (R7), but only for
    the transform contracts the registry marks `is_transform` - a collector output's
    `Metadata` def legitimately allows the empty list, and each contract's own generated
    schema carries its own private copy of the `Metadata` def, so this cannot leak across
    contracts.

    Three model_validator rules are deliberately not encoded here, because plain JSON Schema
    has no keyword that can express them: Entity._check_acceptance_criteria_belong_to_this_entity
    and CoverageMatrixResult._check_acceptance_criteria_belong_to_this_entity both require an
    id field's value to be used as a runtime prefix pattern against a sibling/ancestor
    field's value, which JSON Schema cannot cross-reference; PlannedSummary's
    _check_total_equals_backlog_plus_targeted sums the values of a dynamic-keyed map
    (by_target_version), which JSON Schema has no arithmetic/aggregation keyword for. A
    consumer validating raw JSON against the generated schema alone (not through these
    Pydantic models) will not catch a misowned acceptance-criterion id or an inconsistent
    planned-summary total; this is a documented, accepted schema limitation, not an oversight -
    the same is true of GeneratorReadyResult's SelectionSummary entity-total identity (see
    generator_ready.SelectionSummary docstring).
    """
    defs = schema.get("$defs", {})

    for def_name, rules in _CROSS_FIELD_RULES.items():
        target_def = defs.get(def_name)
        if isinstance(target_def, dict):
            target_def.setdefault("allOf", []).extend(rules)

    if registry.CONTRACTS[contract_id].is_transform:
        metadata_def = defs["Metadata"]
        metadata_def["properties"]["source_inputs"]["minItems"] = 1
        required = metadata_def.setdefault("required", [])
        if "source_inputs" not in required:
            required.append("source_inputs")


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
    """
    raw_schema = model.model_json_schema()
    _rewrite_pattern_maps(raw_schema)
    _inject_own_field_occupancy_enum(raw_schema, field_occupancy_paths(record_roots))
    _inject_cross_field_constraints(raw_schema, contract_id)

    schema: dict[str, Any] = {
        "$schema": SCHEMA_DIALECT,
        "$id": ID_TEMPLATE.format(contract_id=contract_id),
    }
    schema.update(raw_schema)

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
    for contract_id, spec in registry.CONTRACTS.items():
        schema = generate_schema(contract_id, spec.result_model, spec.record_roots)
        path = output_dir / f"{contract_id}-schema.json"
        # Explicit newline: text mode would write CRLF on Windows.
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")
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
    for path in write_schemas():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
