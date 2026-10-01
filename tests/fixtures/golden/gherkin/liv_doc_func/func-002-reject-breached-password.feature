# Golden fixture. Copied verbatim from AbsaOSS/living-doc's
# docs/examples/gherkin/liv_doc_func/func-002-reject-breached-password.feature at commit
# eccbc9e72970e10e8d7e61ffc400c66c252229bd (canon HEAD; the `## Notes` corpus round, PR #43).
# =============================================================================
# LIVING DOC — FUNC-002 · Login Page - Reject Breached Password
# =============================================================================
# status:    planned
# parent:    FEAT-001
# func_type: field_validation
#
# acceptance_criteria:
#
#   AC:FUNC-002-01 (planned)
#     - Returns valid=false when the candidate password appears in the breached-password list.
# =============================================================================

@FUNC_ID:FUNC-002
@domain_authentication
Feature: Login Page - Reject Breached Password
  Rejects a candidate password that the breach check reports as compromised, before the login form is submitted.

  # No scenarios yet: the behaviour is planned.
