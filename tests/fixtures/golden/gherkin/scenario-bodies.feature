# Golden fixture of this repository's own: the Gherkin a scenario's steps, rule and backgrounds come from.
@FUNC_ID:FUNC-001
Feature: Loan fines
  Background:
    Given a member in good standing is signed in

  @AC:FUNC-001-01
  Scenario: A fine shows on its loan
    Given the loans
      | title      | fine |
      | The Hobbit | 0.40 |
    When the member opens the My Loans page
    Then the page shows
      """markdown
      # Fines

      The Hobbit: 0.40
      """

  Rule: A settled fine is left out of the total
    Background:
      Given the member owes 1.20 on "Dune"

    @AC:FUNC-001-02
    Scenario Outline: A <fine-state> fine is left out of the total
      Given the fine on "Dune" is <fine-state>
      Then the total fines owed is 0.00

      @settled_by_member
      Examples: Settled by the member
        | fine-state |
        | paid       |

      Examples: Settled by the library
        | fine-state  |
        | waived      |
        | written-off |
