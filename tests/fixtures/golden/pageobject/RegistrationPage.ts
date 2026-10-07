// Golden fixture. Copied verbatim from AbsaOSS/living-doc's
// docs/examples/pageobject/RegistrationPage.ts at commit
// a80649bd577e6bb135ad8772817bf383ef557d07 (canon HEAD; AC variant keyword as a spelling of Aspect, PR #48).
/* =============================================================================
 * LIVING DOC — FEAT-003 · Registration Page
 * =============================================================================
 * surface_type:          UI
 * route:                 /register
 * owners:                Identity Team
 * purpose:               The screen where a new customer creates an account by entering an email and choosing a password.
 * user_stories:          none
 * functionalities:       none
 * external_dependencies: none
 * feature_dependencies:  FEAT-002
 * page-object:           RegistrationPage.ts
 * ============================================================================= */

import type { Locator, Page } from "@playwright/test";

export class RegistrationPage {
  readonly emailInput: Locator;
  readonly newPasswordInput: Locator;
  readonly submitButton: Locator;

  constructor(private readonly page: Page) {
    this.emailInput = page.getByTestId("registration-email");
    this.newPasswordInput = page.getByTestId("registration-new-password");
    this.submitButton = page.getByTestId("registration-submit");
  }

  async goto(): Promise<void> {
    await this.page.goto("/register");
  }

  async register(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.newPasswordInput.fill(password);
    await this.submitButton.click();
  }
}
