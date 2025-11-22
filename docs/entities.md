# Entities

This document describes the entities used in the TravelCount application.

## Partner

Represents a travel partner who participates in shared expenses during a travel session. Partners are the people who pay for expenses and need to settle costs fairly at the end of the trip.

### Attributes

| Attribute | Type | Description                                    |
|-----------|------|------------------------------------------------|
| name      | str  | The name of the partner (e.g., "Alice", "Bob") |

> NOTE: the attributes isn't database models or ORM models, they represent the state of the business logic. e.g. a `Partner` has a `name` because we need to identify who paid for an expense in the business logic.

### Methods

| Method        | Parameters | Returns | Description                                             |
|---------------|------------|---------|---------------------------------------------------------|
| validate_name | name: str  | bool    | Validates that the partner name is valid (non-empty, no special characters that would break Beancount) |

> NOTE: the methods defined here are part of the domain logic and should not include implementation details related to data storage or external systems. e.g. a `Partner` entity may have a method to `validate_name(name: str)` to ensure the name can be safely used in the business logic.

## Expense

Represents a travel expense entry logged during a travel session. Expenses track spending by partners and can be split among multiple participants.

### Attributes

| Attribute   | Type          | Description                                                      |
|-------------|---------------|------------------------------------------------------------------|
| id          | str           | Unique identifier generated from expense attributes              |
| date        | datetime.date | Date when the expense occurred                                   |
| amount      | Decimal       | Amount of the expense                                            |
| currency    | str           | Currency code (e.g., "USD", "EUR")                               |
| description | str           | Brief description of what the expense was for                    |
| paid_by     | Partner       | The partner who paid for this expense                            |

> NOTE: the attributes represent the business state needed to track and manage expenses. The `id` is generated rather than assigned externally to ensure consistency. The `amount` uses Decimal for precise financial calculations.

### Methods

| Method            | Parameters      | Returns | Description                                                              |
|-------------------|-----------------|---------|--------------------------------------------------------------------------|
| validate_amount   | amount: Decimal | bool    | Validates that the amount is positive and non-zero                       |
| validate_currency | currency: str   | bool    | Validates currency code format (3-letter uppercase)                      |
| generate_id       | -               | str     | Generates consistent unique ID from expense attributes (date, amount, description) |

> NOTE: the methods ensure data integrity at the domain level. The `generate_id()` method provides consistent identification without relying on external ID generation systems.
