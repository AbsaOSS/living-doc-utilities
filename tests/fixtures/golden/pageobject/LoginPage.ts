// Golden fixture. Copied verbatim from AbsaOSS/living-doc's
// docs/examples/pageobject/LoginPage.ts at commit
// eccbc9e72970e10e8d7e61ffc400c66c252229bd (canon HEAD; the `## Notes` corpus round, PR #43).
/* =============================================================================
 * LIVING DOC — FEAT-001 · Login Page
 * =============================================================================
 * surface_type:          UI
 * route:                 /login
 * owners:                Identity Team
 * stub-reason:           Login template carries no test-id attributes yet; surface
 *                        documented from the interface spec. discovered 2026-09-08
 * purpose:               The screen where a registered customer enters an email and password to sign in.
 * user_stories:          US-001
 * functionalities:       FUNC-001, FUNC-002
 * external_dependencies: auth-api
 * page-object:           LoginPage.ts
 * ============================================================================= */

// A PageObject header carries no `status:` and no `deprecated_at:` — see the
// FEAT-001 issue body for why. This surface is documented but not yet
// instrumented — the login template has no test-id attributes — which is what
// `stub-reason:` records. Locators follow once it is instrumented, and
// `stub-reason:` is then removed.
export class LoginPage {
  constructor(private readonly page: import("@playwright/test").Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/login");
  }
}
