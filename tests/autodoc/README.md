# OpenAPI 3.0 Compliance Tests

This directory contains tests to ensure the generated OpenAPI 3.0 documentation is fully compliant with the official OpenAPI 3.0.0 specification.

## Test Coverage

### `test_oai3_compliance.py`

Comprehensive test suite that validates:

1. **Basic Structure**
   - Required top-level fields (`openapi`, `paths`)
   - Proper version string (`3.0.0`)

2. **Operation Objects**
   - Required `operationId` field (unique identifier for each operation)
   - Required `summary` field
   - Required `responses` object
   - Proper handling of invalid HTTP methods (skips non-standard methods like `QUERY`)

3. **OperationId Generation**
   - Follows camelCase convention
   - Properly formats path parameters (e.g., `{id}` becomes `ById`)
   - Maintains proper capitalization (e.g., `{userId}` becomes `ByUserId`, not `ByUserid`)
   - Test cases include:
   - `/health` → `getHealth`
   - `/v3/api/users` → `getV3ApiUsers`
   - `/v3/api/users/{id}` → `getV3ApiUsersById`
   - `/users/{userId}/posts/{postId}` → `putUsersByUserIdPostsByPostId`

4. **Response Objects**
   - Always includes required `description` field
   - Defaults to "Response" when description is empty
   - Proper `content` and `schema` structure

5. **Schema Objects**
   - **Enum schemas**: Uses `nullable: true` instead of including `null` in enum values (OpenAPI 3.0 compliance)
   - **Object schemas with `$ref`**: When using component references, only includes `$ref` without additional properties
   - **Object schemas without `$ref`**: Includes `type`, `properties`, and optional `required` fields
   - **Array schemas**: Proper `type` and `items` structure
   - **Nullable support**: Properly adds `nullable: true` when applicable

6. **Parameter Objects**
   - Always includes required `schema` object
   - Includes `name`, `in`, `required`, and `description` fields
   - Proper handling of empty descriptions

7. **Components**
   - Only included when not empty (no empty `components` object)
   - Proper `schemas` structure for model definitions
   - Proper `securitySchemes` structure

8. **Request Body**
   - Proper structure with `description`, `required`, and `content`
   - Supports `application/json` content type

9. **Multiple Operations on Same Path**
   - Correctly handles multiple HTTP methods on the same path
   - Each operation has unique `operationId`

## Running the Tests

Run all OpenAPI 3.0 compliance tests:

```bash
uv run pytest tests/autodoc/test_oai3_compliance.py -v
```

Run a specific test:

```bash
uv run pytest tests/autodoc/test_oai3_compliance.py::TestOAI3Compliance::test_operation_id_generation -v
```

## Key Compliance Fixes

The following issues were identified and fixed to ensure OpenAPI 3.0 compliance:

1. **Added `operationId` to all operations** - Required by OpenAPI 3.0 spec
2. **Removed `null` from enum values** - Use `nullable: true` instead
3. **Fixed `$ref` usage in objects** - When using `$ref`, no other properties are allowed
4. **Added fallback descriptions** - Ensures required `description` fields are never empty
5. **Filtered invalid HTTP methods** - Removed non-standard methods like `QUERY`
6. **Fixed `components` structure** - Only include when not empty
7. **Added nullable support** - Properly handles `nullable` attribute on schemas

## Validation

Generated OpenAPI specs can be validated against the official schema using tools like:

- [Swagger Editor](https://editor.swagger.io/)
- [OpenAPI Validator](https://github.com/APIDevTools/swagger-parser)
- [Spectral](https://stoplight.io/open-source/spectral)

All generated specs should pass validation without errors or warnings.
