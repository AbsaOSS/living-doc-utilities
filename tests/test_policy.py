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

"""The policy file's model: the default fail list, a project's `check.warn` relaxation, and loading the file."""

import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from living_doc_utilities.policy import DEFAULT_FAIL_CODES, Policy, load_policy

AUTHORING_DIR = Path(__file__).resolve().parents[1] / "living_doc_utilities" / "authoring"


def test_the_default_fail_list_is_every_code_the_authoring_layer_raises():
    """The default fail list is exactly the codes the authoring modules raise, `MISSING_REQUIRED_KEY` among them."""
    raised = {
        name
        for path in AUTHORING_DIR.glob("*.py")
        for name in re.findall(r"\bCode\.([A-Z][A-Z0-9_]*)\b", path.read_text(encoding="utf-8"))
    }

    assert DEFAULT_FAIL_CODES == raised
    assert "MISSING_REQUIRED_KEY" in DEFAULT_FAIL_CODES
    assert len(DEFAULT_FAIL_CODES) == 19


def test_without_a_policy_every_default_code_fails():
    """An empty policy fails on the whole default list."""
    assert Policy().check.fail_codes == DEFAULT_FAIL_CODES


def test_a_code_under_check_warn_only_warns():
    """A code named under `check.warn` leaves the fail list; the others stay in it."""
    policy = Policy.model_validate({"check": {"warn": ["AUTHORING_WARNING", "MISSING_STATUS"]}})

    assert policy.check.fail_codes == DEFAULT_FAIL_CODES - {"AUTHORING_WARNING", "MISSING_STATUS"}


@pytest.mark.parametrize("code", ["NOT_A_CODE", "EMPTY_SOURCE"])
def test_a_code_outside_the_default_list_is_a_policy_error(code):
    """`check.warn` names only codes of the default list: an unknown code, or one the check never fails on, fails."""
    with pytest.raises(ValidationError, match=code):
        Policy.model_validate({"check": {"warn": [code]}})


def test_an_unknown_key_in_the_check_section_is_a_policy_error():
    """The `check` section is closed: a misspelt key fails instead of being ignored."""
    with pytest.raises(ValidationError, match="warns"):
        Policy.model_validate({"check": {"warns": ["AUTHORING_WARNING"]}})


def test_another_gates_section_is_left_to_its_reader():
    """A top-level section other than `check` is accepted, so the gates that add their own sections share the file."""
    policy = Policy.model_validate({"check": {"warn": []}, "coverage": {"baseline": "x"}})

    assert policy.check.fail_codes == DEFAULT_FAIL_CODES


def test_load_policy_reads_the_yaml_file(tmp_path):
    """`load_policy` reads the YAML file into the model."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text("check:\n  # authored by hand\n  warn:\n    - AUTHORING_WARNING\n", encoding="utf-8")

    assert load_policy(path).check.fail_codes == DEFAULT_FAIL_CODES - {"AUTHORING_WARNING"}


def test_an_empty_policy_file_is_the_default_policy(tmp_path):
    """An empty file is the default policy, not an error."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text("", encoding="utf-8")

    assert load_policy(path) == Policy()


@pytest.mark.parametrize("text", ["check:\n", "check:\n  warn:\n  # - AUTHORING_WARNING\n"])
def test_a_section_or_list_left_empty_is_the_default(tmp_path, text):
    """`check:` or `warn:` with no value, its items commented out, is the default, not an error."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text(text, encoding="utf-8")

    assert load_policy(path).check.fail_codes == DEFAULT_FAIL_CODES


@pytest.mark.parametrize(
    "text, key",
    [
        ("check:\n  warn: [NOT_A_CODE]\n  warn: [MISSING_STATUS]\n", "warn"),
        ("check:\n  warn: [MISSING_STATUS]\ncheck: {}\n", "check"),
    ],
)
def test_a_key_written_twice_is_a_policy_error(tmp_path, text, key):
    """A key written twice in one mapping fails, where YAML would silently keep only its last value."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(yaml.YAMLError, match=f"found duplicate key '{key}'"):
        load_policy(path)


def test_a_recursive_alias_is_read_once(tmp_path):
    """A document whose alias refers back to its own anchor still loads: the duplicate-key walk visits it once."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text("check:\n  warn: []\nloop: &self [*self]\n", encoding="utf-8")

    assert load_policy(path).check.fail_codes == DEFAULT_FAIL_CODES


def test_a_policy_file_that_is_not_a_mapping_is_a_policy_error(tmp_path):
    """A file whose top level is not a mapping fails validation."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text("- AUTHORING_WARNING\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_policy(path)


def test_a_policy_file_with_invalid_yaml_raises_a_yaml_error(tmp_path):
    """A file that is not YAML raises `yaml.YAMLError`."""
    path = tmp_path / "living-doc-policy.yaml"
    path.write_text("check: [unclosed\n", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_policy(path)
