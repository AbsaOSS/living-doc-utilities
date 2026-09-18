# Golden fixture. Copied verbatim from AbsaOSS/living-doc's
# docs/examples/gherkin/liv_doc_func/func-001-validate-password-strength.feature at commit
# bfcc402ff998085cbf7bb91a7fd55ea8ac12c911 (the canonical-corpus commit, PRs #25/#26).
# =============================================================================
# LIVING DOC — FUNC-001 · Login Page - Validate Password Strength
# =============================================================================
# status:    active
# parent:    FEAT-001
# func_type: field_validation
#
# acceptance_criteria:
#
#   AC:FUNC-001-01 (v1.0.0 - active)
#     - Returns valid=false when the candidate password fails a complexity rule.
#     - Aspect: minimum-length, character-classes
#
#   AC:FUNC-001-02 (v1.0.0 - active)
#     - Returns valid=true when the candidate password satisfies every complexity rule.
#
#   AC:FUNC-001-03 (planned)
#     - Returns valid=false when the candidate password appears in the breached-password list.
# =============================================================================

@FUNC_ID:FUNC-001
@domain_authentication
Feature: Login Page - Validate Password Strength
  Validates a candidate password against the account complexity policy before the login form is submitted.

  # AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password | aspect: minimum length
  @AC:FUNC-001-01/aspect:minimum-length
  Scenario: Password shorter than the minimum length is rejected
    Given the complexity policy requires at least 12 characters
    When the password "short" is validated
    Then the result is valid=false

  # AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password | aspect: character classes
  @AC:FUNC-001-01/aspect:character-classes
  Scenario: Password missing a required character class is rejected
    Given the complexity policy requires an upper-case letter and a digit
    When the password "lowercaseonly" is validated
    Then the result is valid=false

  # AC:FUNC-001-02 (v1.0.0 - active) is intentionally left UNCOVERED: no scenario
  # carries @AC:FUNC-001-02. Both declared aspects of AC:FUNC-001-01 have a
  # scenario, so that AC is fully covered; FUNC-001-02 is the uncovered counterpart.
  # AC:FUNC-001-03 (planned) is a backlog AC - no target version, not counted.
