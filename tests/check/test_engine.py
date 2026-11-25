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

"""`check`: per-file findings for the changed files, relation findings over the whole corpus."""

import pytest

from living_doc_utilities.check.engine import AuthoredFile, Finding, check

_RULE = "# =============================================================================\n"
_PO_RULE = " * =============================================================================\n"
_AC = "#   AC:{id}-01 (v1.0.0 - active)\n#     - desc\n"


def _us(entity="US-001", keys="# status: active\n# business_value:\n#   - Value.\n", criteria=None, body=""):
    criteria = _AC.format(id=entity) if criteria is None else criteria
    return (
        f"{_RULE}# LIVING DOC — {entity} · Sample Story\n{_RULE}{keys}#\n# acceptance_criteria:\n#\n{criteria}{_RULE}"
        f"\nFeature: Sample Story\n{body}"
    )


def _func(entity="FUNC-001", parent="FEAT-001", status="active"):
    keys = f"# status: {status}\n# parent: {parent}\n# func_type: component_action\n"
    return (
        f"{_RULE}# LIVING DOC — {entity} · Sample Functionality\n{_RULE}{keys}#\n# acceptance_criteria:\n#\n"
        f"{_AC.format(id=entity)}{_RULE}\nFeature: Sample Functionality\n"
    )


def _feat(entity="FEAT-001", functionalities="FUNC-001", user_stories="US-001"):
    return (
        f"/* =============================================================================\n"
        f" * LIVING DOC — {entity} · Sample Page\n{_PO_RULE}"
        f" * surface_type:          UI\n * route:                 /sample\n * owners:                Team\n"
        f" * purpose:               A sample page.\n * user_stories:          {user_stories}\n"
        f" * functionalities:       {functionalities}\n * external_dependencies: none\n"
        f" * page-object:           SamplePage.ts\n{_PO_RULE.rstrip()} */\n\nexport class SamplePage {{}}\n"
    )


# The testbed's FUNC-008 header with the `-` before a criterion's state missing, as in the issue's example.
_FUNC_008_BROKEN = """\
# =============================================================================
# LIVING DOC — FUNC-008 · Catalogue Search Page - Sort Results
# =============================================================================
# status:    active
# parent:    FEAT-001
# func_type: component_action
# not_in_scope:
# - Sorting by popularity, which was retired.
# - Saving a sort order between visits.
#
# acceptance_criteria:
#
#   AC:FUNC-008-01 (v1.0.0 - active)
#     - Results are ordered by relevance by default.
#
#   AC:FUNC-008-02 (v1.0.0 active)
#     - Choosing "Newest first" orders the results by publication date, newest
#       first.
# =============================================================================

@FUNC_ID:FUNC-008
Feature: Catalogue Search Page - Sort Results
  Orders the catalogue results by relevance or by publication date.
"""


def us_file(path, text):
    return AuthoredFile(path, "DocumentedUserStory", text)


def func_file(path, text):
    return AuthoredFile(path, "DocumentedFunctionality", text)


def feat_file(path, text):
    return AuthoredFile(path, "DocumentedFeature", text)


def _corpus(**replaced):
    """The clean corpus: FEAT-001's PageObject, US-001 and FUNC-001; a keyword replaces one file, `None` drops it."""
    files = {
        "page": feat_file("pages/SamplePage.ts", _feat()),
        "us": us_file("features/us-001.feature", _us()),
        "func": func_file("features/func-001.feature", _func()),
        **replaced,
    }
    return [file for file in files.values() if file is not None]


def _codes(findings):
    return [(finding.path, finding.line, finding.code) for finding in findings]


def test_a_clean_change_has_no_finding():
    """A changed file whose header and relations are all sound gets no finding."""
    assert check(_corpus(), {"features/func-001.feature"}) == []


def test_the_issue_example_reports_the_malformed_criterion_and_its_dropped_lines():
    """`AC:FUNC-008-02 (v1.0.0 active)` is `MALFORMED_AC` on line 16, and its two dropped lines warn."""
    corpus = [
        feat_file("CatalogueSearchPage.ts", _feat(functionalities="FUNC-008", user_stories="none")),
        func_file("func-008.feature", _FUNC_008_BROKEN),
    ]

    findings = check(corpus, {"func-008.feature"})

    assert _codes(findings) == [
        ("func-008.feature", 16, "MALFORMED_AC"),
        ("func-008.feature", 17, "AUTHORING_WARNING"),
        ("func-008.feature", 18, "AUTHORING_WARNING"),
    ]
    assert findings[0].message.startswith("Acceptance criterion failed validation: state:")


_BASE_KEYS = "# status: active\n# business_value:\n#   - Value.\n"
_DESCOPED = _AC.replace("active", "descoped").format(id="US-001")


@pytest.mark.parametrize(
    "text, code, line",
    [
        (_us(keys="# status: active\n#   more\n# business_value:\n#   - Value.\n"), "AUTHORING_ERROR", 5),
        (_us(criteria="#   AC:US-001-01 (v1.0.0 active)\n#     - desc\n"), "AUTHORING_WARNING", 11),
        (_us(criteria="#   AC:US-001-01 (v1.0.0 active)\n#     - desc\n"), "MALFORMED_AC", 10),
        (_us(body="\n  @AC:not-valid\n  Scenario: Sc\n    Given a step\n"), "MALFORMED_AC", 16),
        (_us(keys="# status: planned\n# business_value:\n#   - V.\n", criteria=_DESCOPED), "LEGACY_AC_STATE", 10),
        (_us(criteria=_AC.format(id="US-001") + "#     - colour: red, blue\n"), "UNPARSED_AC_LINE", 12),
        (_us(keys=_BASE_KEYS + "# preconditions: text\n"), "UNPARSED_BULLET_LINE", 7),
        (_us(keys=_BASE_KEYS + "# preconditions:\n#   - one\n#  - two\n"), "MISINDENTED_LINE", 9),
        ("Feature: No header\n", "MISSING_ENTITY_ID", 1),
        (_us(keys=_BASE_KEYS + "# foo: bar\n"), "IGNORED_AUTHORED_KEY", 7),
        (_us(keys="# status: done\n# business_value:\n#   - Value.\n"), "MALFORMED_STATUS", 4),
        (_us(keys="# business_value:\n#   - Value.\n"), "MISSING_STATUS", 2),
        (_us(keys="# status: planned\n# business_value:\n#   - Value.\n"), "STATUS_AC_MISMATCH", 2),
        (_us(keys="# status: active\n"), "MISSING_REQUIRED_KEY", 2),
    ],
)
def test_every_per_file_code_is_reported_for_a_changed_feature_file(text, code, line):
    """Each per-file code the parsers raise on a `.feature` file is reported on its line."""
    assert ("us-001.feature", line, code) in _codes(check([us_file("us-001.feature", text)], {"us-001.feature"}))


def test_a_feature_entity_is_read_by_the_page_object_parser():
    """A Feature's file is a PageObject: an unknown key there is `IGNORED_AUTHORED_KEY`."""
    text = _feat().replace(" * page-object:", " * query_params:          x\n * page-object:")

    findings = check([feat_file("SamplePage.ts", text)], {"SamplePage.ts"})

    assert ("SamplePage.ts", 11, "IGNORED_AUTHORED_KEY") in _codes(findings)


def test_the_entity_type_given_picks_the_required_keys():
    """A file given as a User Story is checked against the User Story keys: `business_value:`, not `parent:`."""
    findings = check([us_file("x.feature", _us(keys="# status: active\n"))], {"x.feature"})

    assert [finding.message for finding in findings] == ["Required key 'business_value:' is missing."]


_FUNC_PATH = "features/func-001.feature"


@pytest.mark.parametrize(
    "extra, code, path",
    [
        ({"other": feat_file("pages/O.ts", _feat("FEAT-002", "none"))}, "FEATURE_WITHOUT_FUNCTIONALITY", "pages/O.ts"),
        ({"func": func_file(_FUNC_PATH, _func(parent="FEAT-999"))}, "UNRESOLVED_RELATION", _FUNC_PATH),
        ({"func": func_file(_FUNC_PATH, _func(parent="US-001"))}, "RELATION_TYPE_MISMATCH", _FUNC_PATH),
        ({"other": feat_file("pages/O.ts", _feat("FEAT-002", "FUNC-001"))}, "RELATION_MISMATCH", "pages/O.ts"),
    ],
)
def test_every_relation_code_is_reported_over_the_corpus(extra, code, path):
    """Each relation and Feature status code is reported, on the title line of the file that declares the entity."""
    assert (path, 2, code) in _codes(check(_corpus(**extra), set()))


def test_a_relation_finding_names_its_target():
    """A relation finding sits on no line of its own, so it shows its context, which names the target."""
    corpus = _corpus(page=feat_file("pages/SamplePage.ts", _feat(functionalities="FUNC-001, FUNC-002")))

    assert check(corpus, set()) == [
        Finding(
            "pages/SamplePage.ts",
            2,
            "UNRESOLVED_RELATION",
            "'functionalities' points outside the collected entity set. (entity_id='FEAT-001' target='FUNC-002')",
        )
    ]


def test_a_deleted_file_is_reported_on_the_unchanged_file_whose_relation_it_breaks():
    """With FUNC-001's file deleted, the unchanged PageObject that still lists `FUNC-001` gets the findings."""
    assert _codes(check(_corpus(func=None), set())) == [
        ("pages/SamplePage.ts", 2, "FEATURE_WITHOUT_FUNCTIONALITY"),
        ("pages/SamplePage.ts", 2, "UNRESOLVED_RELATION"),
    ]


def test_a_changed_parent_is_reported_on_the_feature_it_left():
    """A Functionality moved to another Feature leaves its old Feature without it and still listing it."""
    corpus = _corpus(
        other=feat_file("pages/Other.ts", _feat("FEAT-002", "FUNC-001")),
        func=func_file("features/func-001.feature", _func(parent="FEAT-002")),
    )

    findings = _codes(check(corpus, {"features/func-001.feature"}))

    assert ("pages/SamplePage.ts", 2, "RELATION_MISMATCH") in findings
    assert ("pages/SamplePage.ts", 2, "FEATURE_WITHOUT_FUNCTIONALITY") in findings


_CROSS_REFERENCE = """\
/* =============================================================================
 * LIVING DOC — {parent} · Sample Page  [cross-reference]
 * =============================================================================
 * parent-feat:     {parent}
 * route:           /sample/step
 * owners:          Team
 * purpose:         One step of the sample page.
 * page-object:     SampleStepPage.ts
 * ============================================================================= */
"""


def test_a_cross_reference_page_whose_feature_is_gone_is_reported_on_that_page():
    """A cross-reference header's `parent-feat:` that names no Feature drops the page, as the collector reports it."""
    corpus = _corpus(step=feat_file("pages/SampleStepPage.ts", _CROSS_REFERENCE.format(parent="FEAT-009")))

    assert check(corpus, set()) == [
        Finding(
            "pages/SampleStepPage.ts",
            2,
            "UNRESOLVED_RELATION",
            "'parent-feat' points outside the collected entity set; the page is dropped. (target='FEAT-009')",
        )
    ]


def test_a_cross_reference_page_whose_feature_exists_is_clean():
    """A cross-reference header whose `parent-feat:` names a Feature of the corpus gets no finding."""
    corpus = _corpus(step=feat_file("pages/SampleStepPage.ts", _CROSS_REFERENCE.format(parent="FEAT-001")))

    assert check(corpus, {"pages/SampleStepPage.ts"}) == []


def test_a_changed_file_reusing_an_entity_id_gets_its_own_findings():
    """A changed file that reuses another file's id gets its own per-file findings, never the other file."""
    corpus = _corpus(copy=us_file("features/us-001-copy.feature", _us(keys="# business_value:\n#   - Value.\n")))

    findings = _codes(check(corpus, {"features/us-001-copy.feature"}))

    assert ("features/us-001-copy.feature", 2, "MISSING_STATUS") in findings
    assert all(path == "features/us-001-copy.feature" for path, _, _ in findings)


def test_per_file_findings_of_an_unchanged_file_are_not_reported():
    """An unchanged file's own format problems are not the change's: only the changed files are reviewed."""
    corpus = _corpus(us2=us_file("features/us-002.feature", _us(entity="US-002", keys="# status: done\n")))

    assert check(corpus, {"features/func-001.feature"}) == []


def test_findings_are_sorted_by_path_then_line():
    """Findings come in path order, then line order, whatever order the files were given in."""
    files = [us_file("b.feature", _us(keys="# status: done\n# business_value:\n#   - V.\n")), us_file("a.feature", "")]

    findings = check(files, {"a.feature", "b.feature"})

    # The dropped `status: done` falls through to `MISSING_STATUS`, on the title line.
    assert [(f.path, f.line) for f in findings] == [("a.feature", 1), ("b.feature", 2), ("b.feature", 4)]


def test_a_changed_path_that_is_not_a_given_file_is_refused():
    """A changed path the corpus does not hold is the caller's mistake: `ValueError`, never a silent skip."""
    with pytest.raises(ValueError, match="gone.feature"):
        check(_corpus(), {"gone.feature"})


def test_a_path_given_twice_is_refused():
    """Two files with one path would declare their entities twice: `ValueError`."""
    with pytest.raises(ValueError, match="features/us-001.feature"):
        check(_corpus(us2=us_file("features/us-001.feature", _us())), set())
