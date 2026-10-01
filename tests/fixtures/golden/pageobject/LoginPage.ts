// Golden fixture. Copied verbatim from AbsaOSS/living-doc's
// docs/examples/pageobject/LoginPage.ts at commit
// b28820e5940ebc8ee2578fc2663e1464aca83a57 (canon HEAD; a Feature has no deprecated_at, PR #44).
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
