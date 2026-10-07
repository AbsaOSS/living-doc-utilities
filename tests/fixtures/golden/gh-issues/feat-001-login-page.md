<!--
Golden fixture. Copied verbatim from AbsaOSS/living-doc's docs/examples/gh-issues/feat-001-login-page.md
at commit a80649bd577e6bb135ad8772817bf383ef557d07 (canon HEAD; AC variant keyword as a spelling of Aspect, PR #48).
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
