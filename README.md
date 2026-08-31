# Scalable FastAPI Project

Phase 1 creates the core FastAPI structure with dedicated modules for routing,
schemas, models, services, and configuration.

Phase 2 adds SQLAlchemy database integration. The app now creates a SQLAlchemy
engine from `DATABASE_URL`, opens one request-scoped session per API call, and
persists items in an `items` table. Module 12 defines SQLAlchemy ORM models and
matching Pydantic request/response schemas. Module 15 adds request-scoped
transaction management and rollback handling for database failures. Module 16
adds reusable database pagination for list queries. Module 17 adds dynamic
filtering and allowlisted sorting for database-backed list endpoints. Module 18
adds named database constraints, foreign-key enforcement, indexes, and matching
request validations. Module 19 adds soft deletion and restore support for item
resources. Module 20 adds Alembic migrations for database schema management.
Phase 3 starts authentication and authorization. Module 21 adds user
registration with persisted users, normalized credentials, duplicate-account
protection, and password hashing. Module 22 adds email/password login with
signed bearer access tokens. Module 23 adds JWT access-token authentication for
protected endpoints. Module 24 adds opaque refresh tokens with server-side
storage, rotation, and expiration. Modules 25-30 add authenticated-user
dependencies, `/me` APIs, ADMIN/MANAGER/USER roles, fine-grained permissions,
failed-login lockout, password policy enforcement, password recovery, active
sessions, and logout from all devices.

Phase 4 adds real-world backend features: document upload/download/update/delete,
CSV import/export, background notification delivery simulation, scheduled cleanup,
notification read/unread APIs, advanced item search, bulk item operations, audit
logs, and record history.

Phase 5 adds advanced FastAPI features: Redis-ready cache settings with an
in-process cache fallback, API caching and invalidation hooks, rate limiting,
webhook receive/retry APIs, external REST integration, async/concurrent external
processing, and health/readiness checks for database, cache, and external service
configuration.

Phase 6 adds a focused pytest suite, API/authentication tests, external-service
failure coverage, query indexes in migrations, security hardening through shared
authorization guards, Docker Compose for FastAPI/PostgreSQL/Redis, and production
server configuration.

The final business-management layer includes authenticated users, role and
permission checks, employees, customers, products, orders, payments, tasks,
notifications, reports, audit logs, and file management.

## Project Layout

```text
app/
  api/router.py     Top-level API router that mounts API versions
  api/v1/routes/    Versioned API route modules
  api/v2/routes/    Next-version API route modules
  core/             Application configuration
  db/               SQLAlchemy engine and request-scoped session dependency
  models/           Domain and persistence models
  repositories/     Reusable SQLAlchemy repository classes
  schemas/          Request and response schemas
  services/         Business logic
alembic/            Alembic migration environment and version scripts
alembic.ini         Alembic CLI configuration
main.py             ASGI app export
requirements.txt    Runtime dependencies
```

## Run

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Initialize or upgrade the database:

```powershell
.\.venv\Scripts\python.exe scripts\init_database.py --no-admin
$env:ADMIN_PASSWORD="AdminPassword123!"
.\.venv\Scripts\python.exe scripts\init_database.py
```

The runtime migration source is `alembic/versions/`. A readable SQL schema is
also available in `database/schema.sql`.

Health check:

```text
GET /api/v1/health
GET /api/v2/health
```

Items API:

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
GET    /api/v1/auth/password-policy
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
GET    /api/v1/auth/sessions
POST   /api/v1/auth/logout-all
GET    /api/v1/users
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
POST   /api/v1/documents
GET    /api/v1/documents/{document_id}/download
POST   /api/v1/csv/items/import
GET    /api/v1/csv/items/export
GET    /api/v1/search/items?q=desk&sort_by=name&sort_order=asc&skip=0&limit=20
POST   /api/v1/bulk/items
PATCH  /api/v1/bulk/items
DELETE /api/v1/bulk/items
GET    /api/v1/audit/logs
GET    /api/v1/audit/history/{resource_type}/{resource_id}
POST   /api/v1/webhooks
POST   /api/v1/webhooks/{event_id}/retry
GET    /api/v1/integrations/external/status
GET    /api/v1/integrations/external/concurrent
GET    /api/v1/health/ready
POST   /api/v1/business/employees
GET    /api/v1/business/employees
GET    /api/v1/business/employees/{employee_id}
PATCH  /api/v1/business/employees/{employee_id}
DELETE /api/v1/business/employees/{employee_id}
POST   /api/v1/business/customers
GET    /api/v1/business/customers
GET    /api/v1/business/customers/{customer_id}
PATCH  /api/v1/business/customers/{customer_id}
DELETE /api/v1/business/customers/{customer_id}
POST   /api/v1/business/products
GET    /api/v1/business/products
GET    /api/v1/business/products/{product_id}
PATCH  /api/v1/business/products/{product_id}
DELETE /api/v1/business/products/{product_id}
POST   /api/v1/business/orders
GET    /api/v1/business/orders
GET    /api/v1/business/orders/{order_id}
PATCH  /api/v1/business/orders/{order_id}
POST   /api/v1/business/payments
GET    /api/v1/business/payments
GET    /api/v1/business/payments/{payment_id}
PATCH  /api/v1/business/payments/{payment_id}
POST   /api/v1/business/tasks
GET    /api/v1/business/tasks
GET    /api/v1/business/tasks/{task_id}
PATCH  /api/v1/business/tasks/{task_id}
POST   /api/v1/business/tasks/{task_id}/complete
DELETE /api/v1/business/tasks/{task_id}
POST   /api/v1/business/reports
GET    /api/v1/business/reports
GET    /api/v1/business/reports/{report_id}
GET    /api/v1/items?q=search&is_active=true&names=First&names=Second&categories=home-office&min_inventory_count=1&max_rating=5&supplier_name=Office%20Supply%20Co&sort_by=name&sort_order=asc&skip=0&limit=20
GET    /api/v1/items/{item_id}
POST   /api/v1/items
PUT    /api/v1/items/{item_id}
PATCH  /api/v1/items/{item_id}
DELETE /api/v1/items/{item_id}
POST   /api/v1/items/{item_id}/restore
```

Request parameter coverage:

```text
Path parameter:            /api/v1/items/{item_id}
Optional query parameter:  q, is_active
Multiple query parameter:  names=First&names=Second
Pagination query params:   skip, limit
Filter query params:       q, is_active, names, categories, min/max inventory, min/max rating, supplier_name
Sorting query params:      sort_by, sort_order
```

Validation examples:

```json
{
  "name": "Desk Lamp",
  "description": "Adjustable LED desk lamp",
  "category": "home office",
  "tags": ["Lighting", "Desk Setup"],
  "pricing": {
    "base_price": "49.99",
    "discount_percent": 10,
    "currency": "usd"
  },
  "dimensions": {
    "length_cm": 12,
    "width_cm": 12,
    "height_cm": 42
  },
  "inventory_count": 15,
  "metadata": {
    "supplier_code": "DL-100"
  },
  "rating": "4.5",
  "detail": {
    "sku": "DL-100",
    "manufacturer": "BrightDesk",
    "origin_country": "India",
    "warranty_months": 24
  },
  "reviews": [
    {
      "reviewer_name": "Asha",
      "rating": "4.5",
      "comment": "Good light output for desk work"
    }
  ],
  "suppliers": [
    {
      "name": "Office Supply Co",
      "contact_email": "orders@example.com",
      "website": "https://example.com"
    }
  ]
}
```

User registration example:

```json
{
  "username": "tharu_dev",
  "email": "tharu@example.com",
  "password": "Password123!",
  "full_name": "Tharu Dev"
}
```

Registration normalizes usernames and emails to lowercase, rejects duplicate
usernames or emails, stores a PBKDF2-SHA256 password hash, and never returns the
raw password or password hash.

Login example:

```json
{
  "email": "tharu@example.com",
  "password": "Password123!"
}
```

Successful login returns a signed bearer token, an opaque refresh token, token
lifetimes in seconds, and the authenticated user's public profile. Invalid
email/password combinations return the same generic `INVALID_CREDENTIALS` error.

Use the returned access token for protected endpoints:

```text
Authorization: Bearer <access_token>
```

JWT authentication verifies the token signature, expiration, token type, subject
identifier, and active user status before allowing access.

Refresh example:

```json
{
  "refresh_token": "<refresh_token>"
}
```

Refresh tokens are stored server-side as HMAC-SHA256 hashes. Calling
`POST /api/v1/auth/refresh` validates the submitted refresh token, checks that
it has not expired or been revoked, revokes it, creates a replacement refresh
token, and returns a new access-token pair. Reusing an old refresh token returns
`INVALID_REFRESH_TOKEN`.

Custom validation normalizes item names, categories, tags, and currency values.
It also rejects reserved names, duplicate or blank tags, invalid metadata keys,
inactive items with inventory, and discounts on zero-priced items.

Response handling:

```text
POST   /api/v1/auth/register     -> 201 with X-Resource-ID header
POST   /api/v1/auth/login        -> 200 with { access_token, refresh_token, token_type, expires_in, refresh_expires_in, user }
POST   /api/v1/auth/refresh      -> 200 with a rotated token pair
GET    /api/v1/auth/me           -> 200 with the authenticated user's public profile
GET    /api/v1/items              -> 200 with { data, meta } and X-Total-Count
GET    /api/v1/items/{item_id}    -> 200 with ETag and Cache-Control headers
POST   /api/v1/items              -> 201 with Location and X-Resource-ID headers
PUT    /api/v1/items/{item_id}    -> 200 with X-Resource-ID header
PATCH  /api/v1/items/{item_id}    -> 200 with X-Resource-ID header
DELETE /api/v1/items/{item_id}    -> 204 with X-Deleted-ID header and soft deletion
POST   /api/v1/items/{item_id}/restore -> 200 with X-Resource-ID header
```

Response serialization returns monetary values and ratings as formatted strings,
datetimes as ISO 8601 strings, and omits `null` fields from single-item responses.

Dependency injection:

```text
Authentication:      Authorization bearer token is accepted for protected endpoints
Legacy API key:      X-API-Key remains accepted for item write operations
Database session:    Request-scoped DatabaseSession dependency wraps item access
Request validation:  Shared ItemListParams dependency validates list filters
Registration:        POST /api/v1/auth/register is public and creates user accounts
Login:               POST /api/v1/auth/login is public and returns a bearer token
Refresh:             POST /api/v1/auth/refresh is public and rotates refresh tokens
Current user:        GET /api/v1/auth/me requires a valid bearer token
Roles:               ADMIN, MANAGER, and USER are enforced through reusable dependencies
Permissions:         CREATE_USER, UPDATE_USER, DELETE_USER, file, CSV, webhook, audit, and bulk permissions
Security:            Failed login lockout, password reset OTP/token flow, active sessions, logout-all
Operations:          Documents, CSV, notifications, search, bulk operations, audit logs, record history
Production:          Dockerfile, docker-compose.yml, Alembic migrations, Gunicorn config, pytest suite
Business modules:    Employees, customers, products, orders, payments, tasks, notifications, reports, audit logs, files
```

Development API key:

```text
X-API-Key: dev-secret-key
```

API router architecture:

```text
app/main.py              Creates the FastAPI app and includes app.api.router
app/api/router.py        Mounts versioned routers under /api/v1 and /api/v2
app/api/v1/router.py     Groups v1 route modules
app/api/v2/router.py     Groups v2 route modules
```

Versioned APIs:

```text
GET /api/v1/health       Original health response
GET /api/v1/items        Full v1 item CRUD API

GET /api/v2/health       Versioned health response with api_version
GET /api/v2/items        v2 read API using the shared item service
GET /api/v2/items/{id}   v2 item detail API
```

The combined OpenAPI document is available at:

```text
GET /api/openapi.json
```

Exception handling:

```text
AppException                 Base class for custom application exceptions
AuthenticationError          401 for missing or invalid API keys
InvalidCredentialsError      401 for invalid email/password login
AccessTokenError             401 for invalid, expired, or missing bearer tokens
RefreshTokenError            401 for invalid, revoked, or expired refresh tokens
InactiveUserError            403 for inactive user login attempts
ItemNotFoundError            404 for missing item resources
DuplicateItemNameError       409 when item names violate the uniqueness rule
DuplicateUserError           409 when username or email is already registered
DatabaseConstraintViolationError 409 when the database rejects a constraint violation
DatabaseTransactionError     500 when a database transaction fails
RequestValidationError       422 for invalid path, query, or body data
Unhandled exceptions         500 with a generic response body
```

Error responses use a centralized shape:

```json
{
  "detail": "Item not found",
  "error_code": "ITEM_NOT_FOUND",
  "request_id": "..."
}
```

Middleware:

```text
Request ID:        accepts or generates X-Request-ID
Execution timing:  returns X-Process-Time-ms on every handled response
Request logging:   logs method, path, status code, duration, client, and request ID
```

You can pass a request ID explicitly:

```text
X-Request-ID: local-test-123
```

Configuration management:

```text
app/core/config.py          Typed application settings
.env.example                Full local configuration template
.env.development.example    Development overrides
.env.testing.example        Testing overrides
.env.production.example     Production template
```

Settings are loaded from `.env` plus an environment-specific overlay:

```text
APP_ENV=testing     loads .env and .env.testing
ENVIRONMENT=staging loads .env and .env.staging
default             loads .env and .env.development
```

Important settings:

```text
ENVIRONMENT       development, testing, staging, production
DEBUG             must be false in production
DOCS_ENABLED      disables /docs, /redoc, and /api/openapi.json when false
API_KEY           must be changed in production
AUTH_SECRET_KEY   must be changed in production; signs bearer access tokens
ACCESS_TOKEN_EXPIRE_MINUTES  bearer token lifetime
REFRESH_TOKEN_EXPIRE_DAYS    refresh token lifetime
DATABASE_URL      SQLAlchemy database connection string
AUTO_CREATE_TABLES Development convenience toggle for startup create_all
ALLOWED_ORIGINS   comma-separated origins for later CORS modules
SERVER_HOST       preferred host for local server startup
SERVER_PORT       preferred server port
LOG_LEVEL         DEBUG, INFO, WARNING, ERROR, or CRITICAL
```

Database integration:

```text
app/db/session.py          SQLAlchemy engine, SessionLocal, init_db, dependency
app/db/pagination.py       Reusable PaginationParams and Page result objects
app/db/query.py            Reusable SortParams and sort direction types
app/models/base.py         SQLAlchemy declarative base and shared ID/timestamps
app/models/item.py         SQLAlchemy Item ORM model with indexes/constraints
app/models/user.py         SQLAlchemy User ORM model for registered accounts
app/models/refresh_token.py SQLAlchemy RefreshToken ORM model for token rotation
app/repositories/base.py     Reusable generic SQLAlchemy CRUD repository
app/repositories/item_repository.py Item-specific persistence queries
app/repositories/user_repository.py User-specific persistence queries
app/repositories/refresh_token_repository.py Refresh-token persistence and rotation
app/services/auth_service.py Registration business rules and password hashing
app/services/item_service.py Business rules around item CRUD operations
```

Transaction management:

```text
managed_database_session() Opens a request database session and transaction boundary
commit()                  Commits successful requests and translates commit failures
rollback()                Rolls back failed requests and marks the session state
DatabaseTransactionError  Standard 500 response for SQLAlchemy transaction failures
```

Repository writes call `flush()` before returning so database constraint
violations are detected inside the request transaction. On any route, service,
repository, or SQLAlchemy exception, the dependency rolls the session back before
closing it.

Pagination:

```text
PaginationParams  Reusable skip/limit input object for database pagination
Page              Reusable paginated result with items, total, returned, has_next, has_previous
paginate()        Generic repository method that applies offset/limit and total counting
paginate_items()  Item repository/service pagination using the shared pagination layer
```

List responses include pagination metadata:

```json
{
  "meta": {
    "total": 42,
    "skip": 20,
    "limit": 10,
    "returned": 10,
    "has_next": true,
    "has_previous": true
  }
}
```

Advanced filtering and sorting:

```text
q                       Case-insensitive search across item name and description
is_active               Filter active or inactive items
names                   Repeated exact item-name filters
categories              Repeated normalized category filters
min_inventory_count     Minimum inventory count
max_inventory_count     Maximum inventory count
min_rating              Minimum item rating
max_rating              Maximum item rating
supplier_name           Case-insensitive supplier relationship filter
sort_by                 name, category, inventory_count, rating, created_at, updated_at
sort_order              asc or desc
```

Sorting is allowlisted in the repository layer so user input cannot select
arbitrary ORM attributes.

Database constraints:

```text
Unique constraints:
items.name
item_details.item_id
item_details.sku
suppliers.name

Foreign keys:
item_details.item_id -> items.id ON DELETE CASCADE
item_reviews.item_id -> items.id ON DELETE CASCADE
item_suppliers.item_id -> items.id ON DELETE CASCADE
item_suppliers.supplier_id -> suppliers.id ON DELETE CASCADE

Indexes:
items.name
items.category
items.is_active + items.category
items.inventory_count
items.rating
items.created_at
item_details.item_id
item_details.sku
item_reviews.item_id
item_reviews.item_id + item_reviews.rating
item_suppliers.item_id
item_suppliers.supplier_id
suppliers.name

Check constraints:
non-blank item names/categories, item inventory range, inactive items with no
inventory, item/review rating range, non-blank SKUs/reviewer/supplier names,
warranty range, email-like supplier contact values, and http/https supplier URLs.
```

SQLite development databases enable `PRAGMA foreign_keys=ON` on connection so
local foreign-key behavior matches PostgreSQL/MySQL more closely.

Soft delete:

```text
deleted_at              Nullable timestamp that marks a soft-deleted item
DELETE /items/{id}      Sets deleted_at instead of physically deleting the row
GET /items/{id}         Returns 404 for soft-deleted items
GET /items              Excludes soft-deleted items by default
POST /items/{id}/restore Clears deleted_at for a previously soft-deleted item
```

Soft-deleted item rows keep their relationships and unique constraints. That
means an item name remains reserved until the row is restored or physically
removed by a future maintenance workflow.

Database migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic downgrade -1
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Describe change"
.\.venv\Scripts\python.exe -m alembic check
```

Alembic reads the active `DATABASE_URL` from `app.core.config.settings`, so the
same `.env` and `APP_ENV`/`ENVIRONMENT` selection used by the app also controls
migrations. The initial migration is:

```text
alembic/versions/20260830_0001_initial_schema.py
```

For production, set `AUTO_CREATE_TABLES=false` and run Alembic migrations during
deployment. `AUTO_CREATE_TABLES=true` is kept in development/testing examples so
the learning API still starts against a fresh local SQLite database.

Models and schemas:

```text
Item ORM model       app/models/item.py
ItemBase            Shared Pydantic fields and validation
ItemCreate          Request schema for POST and PUT item payloads
ItemPatch/Update    Request schema for partial PATCH item payloads
ItemRead            Response schema created from ORM attributes
ItemListResponse    Response wrapper for paginated item lists
```

CRUD repository layer:

```text
SQLAlchemyRepository Generic get, list, count, create, update, delete, exists methods
ItemRepository       Item list/count filters, name uniqueness lookup, item persistence
ItemService          Validation/business orchestration that delegates DB work to repositories
```

Relationships:

```text
One-to-one:    items.id -> item_details.item_id
One-to-many:   items.id -> item_reviews.item_id
Many-to-many:  items.id -> item_suppliers.item_id -> suppliers.id
```

Related item data can be supplied in `detail`, `reviews`, and `suppliers` when
creating or replacing an item. In `PATCH` requests, omitted relationship fields
are preserved; send an empty `reviews` or `suppliers` list to clear that
collection, or `detail: null` to remove the one-to-one detail row.

Supported database URL formats:

```text
SQLite local default: sqlite:///./app.db
PostgreSQL:           postgresql+psycopg://user:password@localhost:5432/app
MySQL:                mysql+pymysql://user:password@localhost:3306/app
```

Tables can still be created on application startup when `AUTO_CREATE_TABLES` is
enabled. Alembic migrations are the preferred path for schema changes and
production deployments.
