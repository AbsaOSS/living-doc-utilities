<!--
Golden fixture. Copied verbatim from AbsaOSS/living-doc's docs/examples/gh-issues/func-002-reject-breached-password.md
at commit a80649bd577e6bb135ad8772817bf383ef557d07 (canon HEAD; AC variant keyword as a spelling of Aspect, PR #48).
-->
<!--
GitHub issue body for a Functionality mined by collector-gh `doc-issues`.
Label: DocumentedFunctionality    Title: FUNC-002 · Login Page - Reject Breached Password
This form spends its one optional field extension on the Preconditions section.
Layout: see ../README.md (GitHub issue-body layout)
-->

## Description

Rejects a candidate password that the breach check reports as compromised, before the login form is submitted.

## Status

planned

## Parent Feature

FEAT-001

## Func Type

field_validation

## Preconditions

- The breach check is reachable from the login surface.

## Acceptance Criteria

### AC:FUNC-002-01 (planned)

- Returns valid=false when the candidate password appears in the breached-password list.
