<!--
Golden fixture. Copied verbatim from AbsaOSS/living-doc's docs/examples/gh-issues/us-001-customer-login.md
at commit bfcc402ff998085cbf7bb91a7fd55ea8ac12c911 (the canonical-corpus commit, PRs #25/#26).
-->
<!--
GitHub issue body for a User Story mined by collector-gh `doc-issues`.
Label: DocumentedUserStory        Title: US-001 · Customer Login
Layout: see ../README.md (GitHub issue-body layout)
-->

## Description

As a registered customer, I can sign in with my email and password, so that I can reach my account area.

## Status

active

## Business Value

- Registered customers can reach their account area, so returning users convert without friction.

## Not In Scope

- Social-identity (OAuth) sign-in — tracked separately as US-002.

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- A customer who submits valid credentials lands on the account dashboard.

### AC:US-001-02 (v1.0.0 - active)

- An inline error is shown when the customer submits invalid credentials, without leaving the login screen.

### AC:US-001-03 (v1.1.0 - planned)

- A customer who forgot the password can request a reset link from the login screen.

### AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)

- A "Remember me" choice keeps the customer signed in across browser restarts.
