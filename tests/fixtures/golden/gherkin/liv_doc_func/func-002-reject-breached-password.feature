# Golden fixture. Copied verbatim from AbsaOSS/living-doc's
# docs/examples/gherkin/liv_doc_func/func-002-reject-breached-password.feature at commit
# b28820e5940ebc8ee2578fc2663e1464aca83a57 (canon HEAD; a Feature has no deprecated_at, PR #44).
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
