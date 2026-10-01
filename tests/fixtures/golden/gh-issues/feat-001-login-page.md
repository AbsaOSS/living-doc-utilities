<!--
Golden fixture. Copied verbatim from AbsaOSS/living-doc's docs/examples/gh-issues/feat-001-login-page.md
at commit b28820e5940ebc8ee2578fc2663e1464aca83a57 (canon HEAD; a Feature has no deprecated_at, PR #44).
-->
<!--
GitHub issue body for a Feature mined by collector-gh `doc-issues`.
Label: DocumentedFeature    Title: FEAT-001 · Login Page
A Feature carries no `## Status` and no `## Deprecated At`: its state is derived from its
Functionalities, and a Feature has no deprecation date at all.
`## Notes` is the corpus's single instance of the entity-level note section.
Layout: see ../README.md (GitHub issue-body layout)
-->

## Description

The screen where a registered customer enters an email and password to sign in.

## Surface Type

UI

## Owners

Identity Team

## User Stories

US-001

## Functionalities

FUNC-001, FUNC-002

## External Dependencies

auth-api

## Notes

- The sign-in form markup comes from the shared identity template, so the surface can change without
  any commit in this repository.
- The customer-facing name of this screen is "Sign in"; "Login Page" is the internal name the team and
  the test suite use.
