# Refactoring Plan - try-apache

This document outlines suggested refactors to improve code consistency, testability, and maintainability of the Siloed WSGI architecture.

## Architectural Improvements

### 1. Standardize Request/Response Handling
Currently, handlers like `login.py` manually parse WSGI input, while others use decorators. We should unify this.
*   **Action**: Create a `@json_body` decorator in `middleware.py`.
*   **Action**: Update `@json_response` and `@html_response` to handle complex return types (e.g., a `Response` object or a tuple of `(body, status, headers)`).

### 2. Eliminate Import Hacks
The project uses `try...except ImportError` blocks to handle differences between local development and deployed silo environments.
*   **Action**: Standardize the `PYTHONPATH` in `wsgi.py` and the test runner so that `from infra.middleware import ...` works everywhere.
*   **Action**: Remove the import shims from all endpoint files.

### 3. Decouple JWT Logic
The `require_jwt` decorator is currently responsible for configuration, cookie parsing, file I/O (reading public keys), and JWT validation.
*   **Action**: Move JWT validation and token extraction logic into `infra/providers.py` or a new `infra/auth_utils.py`.
*   **Action**: Make the public key path configurable via the `Container`.

### 4. Improve Dependency Injection
The current `Container` in `providers.py` is a minimal shim.
*   **Action**: Formalize the provider pattern to allow for easier mocking in tests without relying on global state.

---

## Task List

### Phase 1: Middleware & Core Infrastructure
- [x] **[INFRA-01]** Implement `@json_body` decorator in `infra/middleware.py`.
- [x] **[INFRA-02]** Enhance `@json_response` to support custom headers (for cookies) and status codes.
- [x] **[INFRA-03]** Extract JWT validation logic to `infra/providers.py`.
- [x] **[INFRA-04]** Standardize `PYTHONPATH` and remove `try...except` import shims in:
    - [x] `endpoints/auth/login.py`
    - [x] `endpoints/auth/logout.py`
    - [x] `endpoints/auth/refresh.py`
    - [x] `endpoints/home/index.py`
    - [x] `endpoints/reports/index.py`

### Phase 2: Endpoint Refactoring
- [x] **[AUTH-01]** Refactor `login.py` to use `@json_body` and the enhanced `@json_response`.
- [x] **[AUTH-02]** Refactor `refresh.py` to use the enhanced `@json_response`.
- [x] **[AUTH-03]** Refactor `logout.py` to use a consistent response pattern.

### Phase 3: Routing & Reliability
- [ ] **[ROUTE-01]** Update `wsgi.py` to be more resilient to missing handlers and provide better error logging.
- [ ] **[ROUTE-02]** Ensure `manifest.yaml` is the single source of truth for all routing logic.

### Phase 4: Testing & Validation
- [ ] **[TEST-01]** Add unit tests for new middleware decorators.
- [ ] **[TEST-02]** Create an integration test suite that simulates the full login -> access -> refresh lifecycle.
