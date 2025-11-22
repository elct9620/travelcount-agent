Validation
===

When updating the beancount file we should make same validation like `bean-check` command does.

## Protocol

This feature is validation module for low-level component. It will be invoked automatically when any beancount-related feature modifies the beancount file.

## Data Model

N/A

## Scenarios

```gherkin
Feature: Validate Beancount file updates

    Scenario: Valid Beancount file update
        Given an updated Beancount file with correct syntax
          """
            2024-01-01 open Assets:Travel:Partners:Alice USD
            2024-01-01 open Assets:Travel:Partners:Bob USD
          """
        When the user tries to interact with accounting data
        Then the agent should proceed without errors

    Scenario: Invalid Beancount file update
        Given an updated Beancount file with incorrect directive
          """
            2024-01-01 open Assets:Travel:Partners:Alice USD
            2024-01-01 close Assets:Travel:Partners:Alice USD
            2024-01-01 open Assets:Travel:Partners:Alice USD
          """
        When the user tries to interact with accounting data
        Then the agent should respond with internal error indicating validation failure
        And rollback the beancount file to previous valid state
```

This ensures the beancount file can be exported and used without issues. Each feature's design should not cause any beancount validation errors.
