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
