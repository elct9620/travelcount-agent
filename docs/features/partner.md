Partner
===

The partner feature allows TravelCount to add multiple travel partners to a single travel session. We can track expenses for each partner to make sure everyone pays their fair share.

## Protocol

This feature is a Function Tool in ADK. It defines the following interface:

```python
def partners(operation: str, name: str = None) -> dict:
    """
    Manage travel partners.

    Args:
        operation (str): The operation to perform. Can be "add", "remove", or "list".
        name (str, optional): The name of the partner to add or remove. Required for "add" and "remove" operations.

    Returns:
        dict: A dictionary containing the result of the operation.
    """
```

## Data Model

The partner data is represented as Beancount accounts saved in the session's Beancount file.

```beancount
1970-01-01 open Assets:Travel:Partners:Alice USD
1970-01-01 open Assets:Travel:Partners:Bob USD
```

## Validation

Each operation should produce a valid Beancount file. The following is policies to ensure ledger correctness:

- Adding a partner that already exists should return an error.
- Adding a partner back remove "close" directive instead of opening a new account.
- Removing a partner can use "close" directive to close the account.
- Removing a partner already has transactions should return an error.
- Renaming partners is allowed by replacing the account name in all transactions.

## Scenarios

Following are scenarios in Gherkin format to illustrate how the agent handles partner operations.

```gherkin
Feature: Manage travel partners

  Scenario: Add a new partner
    Given a travel session "Summer Vacation"
    When the user inputs "Add a partner named Alice"
    Then the agent should respond "Partner 'Alice' has been added."

  Scenario: Remove an existing partner
    Given a travel session "Summer Vacation" with partner "Alice"
    When the user inputs "Remove the partner named Alice"
    Then the agent should respond "Partner 'Alice' has been removed."

  Scenario: List all partners
    Given a travel session "Summer Vacation" with partners "Alice" and "Bob"
    When the user inputs "List all my travel partners"
    Then the agent should respond "Your travel partners are: Alice, Bob."

  Scenario: Attempt to remove a non-existent partner
    Given a travel session "Summer Vacation" with partner "Alice"
    When the user inputs "Remove the partner named Bob"
    Then the agent should respond "Partner 'Bob' does not exist."

  Scenario: Attempt to add a duplicate partner
    Given a travel session "Summer Vacation" with partner "Alice"
    When the user inputs "Add a partner named Alice"
    Then the agent should respond "Partner 'Alice' already exists."
```
