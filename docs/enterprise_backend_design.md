# Enterprise Backend Design

This project is structured as a business-management backend, not a collection of
standalone CRUD endpoints. The API exposes CRUD where it is useful, but important
workflows are modeled as business operations with validation, side effects, audit
logging, and explicit error contracts.

## Architecture

The application follows a layered FastAPI architecture:

- `api/v1/routes`: HTTP contract, dependency wiring, request/response models.
- `schemas`: Pydantic contracts for validation and serialization.
- `services`: business workflows such as order creation, payment recording,
  task completion, authentication, password recovery, and report generation.
- `repositories`: SQLAlchemy persistence helpers and shared query patterns.
- `models`: database schema and indexes.
- `core`: configuration, authentication, authorization, security, middleware,
  and exception handling.

Routes should stay thin for workflow-heavy modules. Business rules that combine
multiple records or produce side effects belong in services.

## Database Design

The schema separates platform concerns from business concerns:

- Authentication: `users`, `refresh_tokens`, `password_reset_tokens`,
  `user_sessions`.
- Authorization: user `role` plus explicit `permissions`, resolved through
  `ROLE_PERMISSIONS`.
- Operations: `documents`, `notifications`, `webhook_events`, `scheduled_jobs`.
- Governance: `audit_logs`, `record_history`.
- Business domain: `employees`, `customers`, `products`, `sales_orders`,
  `order_line_items`, `payments`, `work_tasks`, `reports`.

Important lookup and reporting fields are indexed, including emails, SKUs, order
status, payment status, task status, audit resource keys, and record-history
resource keys.

## API Contracts

The main API namespace is `/api/v1`.

Authentication contracts:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /auth/sessions`
- `POST /auth/logout-all`

Business contracts:

- Employees: `/business/employees`
- Customers: `/business/customers`
- Products: `/business/products`
- Orders: `/business/orders`
- Payments: `/business/payments`
- Tasks: `/business/tasks`
- Reports: `/business/reports`

Operational contracts:

- Files: `/documents`
- Notifications: `/notifications`
- Audit/history: `/audit/logs`, `/audit/history/{resource_type}/{resource_id}`
- CSV: `/csv/items/import`, `/csv/items/export`
- Search: `/search/items`
- Webhooks: `/webhooks`
- Health: `/health`, `/health/ready`

## Business Logic

Implemented workflows include:

- Creating an order validates the customer, validates each product, rejects
  inactive products, checks stock, creates immutable order line snapshots,
  reduces product stock, totals the order, writes audit logs, and creates a
  notification.
- Creating a payment validates the order, rejects cancelled orders, prevents
  overpayment, records the payment, and marks the order paid when the outstanding
  balance reaches zero.
- Completing a task is idempotent and records audit activity.
- Generating reports computes current sales, customer, task, or inventory
  summaries and stores the generated result.
- Updating important records writes prior versions to `record_history`.

## Authentication And Authorization

Authentication uses signed access tokens and server-side refresh-token rotation.
Access tokens include a session id, and `/auth/logout-all` revokes active sessions
and refresh tokens. Password reset uses a short-lived token plus OTP, with password
history checks to prevent recent password reuse.

Authorization is role and permission based:

- `ADMIN` receives all permissions.
- `MANAGER` receives operational business permissions.
- `USER` receives limited read/task/report permissions.

Permission dependencies are reusable and support bearer-token users plus the
legacy development API key.

## Error Handling

The app uses centralized exception handlers. Domain errors should raise typed
application exceptions:

- Authentication failures return `401`.
- Authorization failures return `403`.
- Missing resources return `404`.
- Business-rule violations return `409`.
- Rate limits return `429`.

Unexpected exceptions still return `500`, but business services should avoid
using generic exceptions for expected rule failures.

## Tests

The test suite covers:

- Registration, login, `/me`, and logout-all session invalidation.
- Password reset token and OTP flow.
- API-key item writes and readiness checks.
- Webhook failure capture.
- Business workflow from employee/customer/product through order, payment, task,
  and report generation.
- Business-rule rejection for insufficient stock.

Fresh Alembic migrations are also verified against a temporary SQLite database.
