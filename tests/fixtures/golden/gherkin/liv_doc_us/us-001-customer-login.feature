# Golden fixture. Copied verbatim from AbsaOSS/living-doc's
# docs/examples/gherkin/liv_doc_us/us-001-customer-login.feature at commit
# bfcc402ff998085cbf7bb91a7fd55ea8ac12c911 (the canonical-corpus commit, PRs #25/#26).
# =============================================================================
# LIVING DOC — US-001 · Customer Login
# =============================================================================
# status:          active
# business_value:
#   - Registered customers can reach their account area, so returning users
#     convert without friction.
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - A customer who submits valid credentials lands on the account dashboard.
#     preconditions:
#       - A registered customer account exists and is not locked.
#
#   AC:US-001-02 (v1.0.0 - active)
#     - An inline error is shown when the customer submits invalid credentials,
#       without leaving the login screen.
#
#   AC:US-001-03 (v1.1.0 - planned)
#     - A customer who forgot the password can request a reset link from the
#       login screen.
#
#   AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)
#     - A "Remember me" choice keeps the customer signed in across browser
#       restarts.
# =============================================================================

@US_ID:US-001
@domain_authentication
Feature: Customer Login
  As a registered customer, I can sign in with my email and password, so that I can reach my account area.

  # AC:US-001-01 (v1.0.0 - active) - valid credentials land on the account dashboard
  @AC:US-001-01
  Scenario: Customer signs in with valid credentials
    Given a registered customer is on the login screen
    When the customer submits valid credentials
    Then the account dashboard is displayed

  # AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0) - a remembered session survives a restart
  @AC:US-001-04
  Scenario: Remembered customer is still signed in after a browser restart
    Given a registered customer signed in with "Remember me" selected
    When the customer reopens the browser
    Then the account dashboard is displayed

  # AC:US-001-02 (v1.0.0 - active) is intentionally left UNCOVERED: no scenario
  # carries @AC:US-001-02, so it is reported as an uncovered AC in the coverage
  # matrix. AC:US-001-01 above is the covered counterpart, and AC:US-001-04 shows
  # that a deprecated AC is still counted.
  # AC:US-001-03 (v1.1.0 - planned) targets v1.1.0 and is not counted either way.
