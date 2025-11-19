# Entities

This document describes the entities used in the TravelCount application.

## [ENTITY_NAME]

[Description of the entity, explaining its domain meaning and purpose.]

### Attributes

| Attribute        | Type        | Description                    |
|------------------|-------------|--------------------------------|
| [attribute_name] | [data_type] | [Description of the attribute] |
| ...              | ...         | ...                            |

> NOTE: the attributes isn't database models or ORM models, they represent the state of the business logic. e.g. an `Account` has a `name` because we need to know the name of the account in the business logic.

### Methods

| Method           | Parameters                  | Returns       | Description                              |
|------------------|-----------------------------|---------------|------------------------------------------|
| [method_name]    | [param1: type, param2: type]| [return_type] | [Description of the method]              |
| ...              | ...                         | ...           | ...                                      |

> NOTE: the methods defined here are part of the domain logic and should not include implementation details related to data storage or external systems. e.g. an `Account` entity may have a method to `rename(new_name: str)` to change its name in the business logic because our business logic requires renaming accounts.

## [ANOTHER_ENTITY_NAME]

[Description of another entity, explaining its domain meaning and purpose.]

### Attributes

| Attribute        | Type        | Description                    |
|------------------|-------------|--------------------------------|
| [attribute_name] | [data_type] | [Description of the attribute] |
| ...              | ...         | ...                            |

### Methods

| Method           | Parameters                  | Returns       | Description                              |
|------------------|-----------------------------|---------------|------------------------------------------|
| [method_name]    | [param1: type, param2: type]| [return_type] | [Description of the method]              |
| ...              | ...                         | ...           | ...                                      |
