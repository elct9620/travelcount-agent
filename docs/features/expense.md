Expense
===

The expense feature allows users to log their travel-related expenses based on the session (per-trip) and partner (per-person) that can analyze and split costs accordingly.

## Protocol

This feature is a Function Tool in ADK. It defines the following interface:

```python
def log_expense(amount: float, currency: str, description: str, paid_by: str = None) -> dict:
    """
    Log a travel expense.

    Args:
        amount (float): The amount of the expense.
        currency (str): The currency of the expense (e.g., "USD").
        description (str): A brief description of the expense.
        paid_by (str, optional): The name of the partner who paid for the expense. If not provided, defaults to the first partner in the session.

    Returns:
        dict: A dictionary containing the result of the operation.
    """

def split_expense(expense_id: str, partners: list, ratio: list = None) -> dict:
    """
    Split an expense among travel partners. Default is an equal split.

    Args:
        expense_id (str): The ID of the expense to split.
        partners (list): A list of partner names to split the expense among.

    Returns:
        dict: A dictionary containing the result of the operation.
    """

def get_expenses(range: str = "all", aggregate: bool = True) -> list:
    """
    Retrieve all logged expenses for the current travel session.

    Args:
        range (str, optional): The time range for the expenses to retrieve. Defaults to "all".
        aggregate (bool, optional): Whether to aggregate expenses by partner. Defaults to True.
            - If True: Returns total expense amount for each partner (their share after splits)
            - If False: Returns expense items showing each partner's share per expense
                       (e.g., "Hotel shared by Bob: $50", "Hotel shared by Alice: $50")

    Returns:
        list: A list of dictionaries, each representing an expense or aggregated partner total.
            When aggregate=True:
                [{"partner": "Alice", "total_expense": 85.00, "currency": "USD"}, ...]
            When aggregate=False:
                [{"description": "Hotel Stay", "shared_by": "Alice", "amount": 50.00}, ...]
    """
```

## Data Model

When log an expense, the expense data will logged as shared expense entries in the session's Beancount file.

```beancount
1970-01-01 * "Lunch at Cafe"
  Expenses:Travel:Food          50.00 USD
  Assets:Travel:Partners:Alice
```

After splitting an expense, the split details will be recorded as transfer entries among partners in the Beancount file.

```beancount
1970-01-01 * "Split Lunch Expense"
  Assets:Travel:Partners:Alice   -25.00 USD
  Assets:Travel:Partners:Bob     25.00 USD
```

Split amounts are displayed with appropriate precision for the currency (e.g., 2 decimal places for USD/EUR, whole numbers for JPY/KRW).

## Scenarios

Following are scenarios in Gherkin format to illustrate how the agent handles expense logging and splitting.

```gherkin
Feature: Manage travel expenses

  Background:
    Given a travel session "Summer Vacation"
    And the "Summer Vacation" session has following partners:
      | Name  |
      | Alice |
      | Bob   |

    Scenario: Log a new expense paid by a specific partner
        When the user inputs "Log an expense of $100 for 'Hotel Stay' paid by Alice"
        Then the agent should respond "Expense of $100 for 'Hotel Stay' has been logged, paid by Alice."

    Scenario: Log a new expense without specifying a partner
        When the user inputs "Log an expense of $50 for 'Lunch at Cafe'"
        Then the agent should respond "Expense of $50 for 'Lunch at Cafe' has been logged, paid by Alice."

    Scenario: Split an expense equally among partners
        Given an expense of $100 for "Hotel Stay" logged, paid by Alice
        When the user inputs "Split the 'Hotel Stay' expense equally between Alice and Bob"
        Then the agent should respond "Expense 'Hotel Stay' has been split equally between Alice and Bob."

    Scenario: Split an expense with specified ratios
        Given an expense of $150 for "City Tour" logged, paid by Bob
        When the user inputs "Split the 'City Tour' expense between Alice and Bob in a 70-30 ratio"
        Then the agent should respond "Expense 'City Tour' has been split between Alice and Bob in a 70-30 ratio."

    Scenario: Retrieve all expenses for the session (showing individual shares)
        Given multiple expenses logged for the "Summer Vacation" session
          | Description       | Amount | Paid By | Date       |
          | Hotel Stay        | 100.00 | Alice   | 2024-06-01 |
          | Lunch at Cafe     | 50.00  | Alice   | 2024-06-02 |
        And splits have been made accordingly
          | Description   | Split Between | Ratio |
          | Hotel Stay    | Alice, Bob    | 50-50 |
          | Lunch at Cafe | Alice, Bob    | 70-30 |
        When the user "Alice" inputs "Show me all my expenses for the 'Summer Vacation' trip"
        Then the agent should respond with a list showing Alice's share of each expense.
          | Description   | Amount | Paid By |
          | Hotel Stay    | 50.00  | Alice   |
          | Lunch at Cafe | 35.00  | Alice   |

    Scenario: Retrieve aggregated expenses for a partner
        Given multiple expenses logged for the "Summer Vacation" session
          | Description       | Amount | Paid By | Date       |
          | Hotel Stay        | 100.00 | Alice   | 2024-06-01 |
          | Lunch at Cafe     | 50.00  | Alice   | 2024-06-02 |
        And splits have been made accordingly
          | Description   | Split Between | Ratio |
          | Hotel Stay    | Alice, Bob    | 50-50 |
          | Lunch at Cafe | Alice, Bob    | 70-30 |
        When the user "Bob" inputs "Show me my total expenses for the 'Summer Vacation' trip"
        Then the agent should respond "Your total expenses for the 'Summer Vacation' trip amount to $65.00."

    Scenario: Retrieve expenses within a specific date range
        Given multiple expenses logged for the "Summer Vacation" session
          | Description       | Amount | Paid By | Date       |
          | Hotel Stay        | 100.00 | Alice   | 2024-06-01 |
          | Lunch at Cafe     | 50.00  | Alice   | 2024-06-02 |
          | City Tour         | 150.00 | Bob     | 2024-06-05 |
        And splits have been made accordingly
          | Description   | Split Between | Ratio |
          | Hotel Stay    | Alice, Bob    | 50-50 |
          | Lunch at Cafe | Alice, Bob    | 70-30 |
          | City Tour     | Alice, Bob    | 70-30 |
        When the user "Alice" inputs "Show me my expenses for the 'Summer Vacation' trip from June 1 to June 3"
        Then the agent should respond with a list of expenses for Alice within the specified date range.
          | Description   | Amount | Paid By |
          | Hotel Stay    | 50.00  | Alice   |
          | Lunch at Cafe | 35.00  | Alice   |

    Scenario: Retrieve expenses without aggregation
        Given multiple expenses logged for the "Summer Vacation" session
          | Description       | Amount | Paid By | Date       |
          | Hotel Stay        | 100.00 | Alice   | 2024-06-01 |
          | Lunch at Cafe     | 50.00  | Alice   | 2024-06-02 |
        And splits have been made accordingly
          | Description   | Split Between | Ratio |
          | Hotel Stay    | Alice, Bob    | 50-50 |
          | Lunch at Cafe | Alice, Bob    | 70-30 |
        When the user "Bob" inputs "Show me all my expenses for the 'Summer Vacation' trip without aggregation"
        Then the agent should respond with a detailed list of all expenses for Bob.
          | Description   | Amount | Paid By |
          | Hotel Stay    | 50.00  | Alice   |
          | Lunch at Cafe | 15.00  | Alice   |

    Scenario: Attempt to split a non-existent expense
        When the user inputs "Split the expense with ID 'EXP999' between Alice and Bob"
        Then the agent should respond "Expense with ID 'EXP999' does not exist."

    Scenario: Attempt to log an expense with invalid amount
        When the user inputs "Log an expense of $-20 for 'Invalid Expense'"
        Then the agent should respond "The amount must be a positive number."

    Scenario: Attempt to split an expense with invalid ratios
        Given an expense of $100 for "Dinner" logged, paid by Alice
        When the user inputs "Split the 'Dinner' expense between Alice and Bob in a 60-50 ratio"
        Then the agent should respond "The sum of the split ratios must equal 100%."
```
