# Golden fixture. Copied verbatim from AbsaOSS/living-doc's
# docs/examples/gherkin/liv_doc_func/func-001-validate-password-strength.feature at commit
# a80649bd577e6bb135ad8772817bf383ef557d07 (canon HEAD; AC variant keyword as a spelling of Aspect, PR #48).
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
#     - Aspect: minimum-length, character-classes, no-username
#
#   AC:FUNC-001-02 (v1.0.0 - active)
#     - Returns valid=true when the candidate password satisfies every complexity rule.
#
#   AC:FUNC-001-03 (v1.0.0 - active)
#     - Shows the failed {rule} under the password field.
#     - rule: minimum-length, character-classes, no-username
# =============================================================================

@FUNC_ID:FUNC-001
@domain_authentication
Feature: Login Page - Validate Password Strength
  Validates a candidate password against the account complexity policy before the login form is submitted.

  # This Functionality calls nothing: the complexity policy is checked client-side. The
  # breached-password check is FUNC-002, which declares the dependency on the API Feature.

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

  # AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password | aspect: no username
  @AC:FUNC-001-01/aspect:no-username
  Scenario: Password containing the username is rejected
    Given the complexity policy forbids the account username "jdoe" in the password
    When the password "jdoe-Secure-2026" is validated
    Then the result is valid=false

  # AC:FUNC-001-03 (v1.0.0 - active) - shows the failed rule | rule: minimum length
  @AC:FUNC-001-03/rule:minimum-length
  Scenario: Password shorter than the minimum length shows the minimum-length rule
    Given the complexity policy requires at least 12 characters
    When the password "short" is validated
    Then the minimum-length rule is shown under the password field

  # AC:FUNC-001-02 (v1.0.0 - active) is intentionally left UNCOVERED: no scenario
  # carries @AC:FUNC-001-02. Every declared aspect of AC:FUNC-001-01 has a
  # scenario, so that AC is fully covered; FUNC-001-02 is the uncovered counterpart.
  # AC:FUNC-001-03 declares three rule values and only minimum-length has a
  # scenario, so it is partly covered: 1/3.
