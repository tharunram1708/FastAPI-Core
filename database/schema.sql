-- Enterprise Business Management Backend schema.
-- Alembic is the source of truth for runtime migrations; this file is a
-- readable SQL contract for the database design.

CREATE TABLE IF NOT EXISTS users (
    id CHAR(32) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    permissions JSON NOT NULL DEFAULT '[]',
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    password_changed_at TIMESTAMP,
    password_history JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    replaced_by_token_id CHAR(32) REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    otp_hash VARCHAR(64),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_id CHAR(32) REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    user_agent VARCHAR(255),
    ip_address VARCHAR(64),
    revoked_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employees (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    employee_code VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(40),
    department VARCHAR(80) NOT NULL DEFAULT 'operations',
    title VARCHAR(120) NOT NULL,
    salary NUMERIC(12, 2),
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id CHAR(32) PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(40),
    billing_address TEXT,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id CHAR(32) PRIMARY KEY,
    sku VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    category VARCHAR(80) NOT NULL DEFAULT 'general',
    unit_price NUMERIC(12, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id CHAR(32) PRIMARY KEY,
    order_number VARCHAR(80) NOT NULL UNIQUE,
    customer_id CHAR(32) NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    notes TEXT,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_line_items (
    id CHAR(32) PRIMARY KEY,
    order_id CHAR(32) NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id CHAR(32) REFERENCES products(id) ON DELETE SET NULL,
    sku VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id CHAR(32) PRIMARY KEY,
    order_id CHAR(32) NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    customer_id CHAR(32) NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    amount NUMERIC(12, 2) NOT NULL,
    method VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    transaction_reference VARCHAR(160),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_tasks (
    id CHAR(32) PRIMARY KEY,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    assigned_to_user_id CHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    employee_id CHAR(32) REFERENCES employees(id) ON DELETE SET NULL,
    customer_id CHAR(32) REFERENCES customers(id) ON DELETE SET NULL,
    order_id CHAR(32) REFERENCES sales_orders(id) ON DELETE SET NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    priority VARCHAR(40) NOT NULL DEFAULT 'normal',
    due_at TIMESTAMP,
    completed_at TIMESTAMP,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id CHAR(32) PRIMARY KEY,
    owner_id CHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL DEFAULT 'application/octet-stream',
    storage_path VARCHAR(500) NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    description TEXT,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(80) NOT NULL DEFAULT 'general',
    read_at TIMESTAMP,
    delivered_at TIMESTAMP,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id CHAR(32) PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    report_type VARCHAR(80) NOT NULL,
    filters JSON NOT NULL DEFAULT '{}',
    generated_by_id CHAR(32),
    status VARCHAR(40) NOT NULL DEFAULT 'completed',
    result JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id CHAR(32) PRIMARY KEY,
    actor_id CHAR(32),
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(80),
    ip_address VARCHAR(64),
    details JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS record_history (
    id CHAR(32) PRIMARY KEY,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(80) NOT NULL,
    version INTEGER NOT NULL,
    previous_data JSON NOT NULL DEFAULT '{}',
    changed_by_id CHAR(32),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id CHAR(32) PRIMARY KEY,
    source VARCHAR(120) NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSON NOT NULL DEFAULT '{}',
    status VARCHAR(40) NOT NULL DEFAULT 'received',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id CHAR(32) PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    result JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_employees_department ON employees(department);
CREATE INDEX IF NOT EXISTS ix_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS ix_products_category ON products(category);
CREATE INDEX IF NOT EXISTS ix_sales_orders_customer_id ON sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_sales_orders_status ON sales_orders(status);
CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS ix_work_tasks_status ON work_tasks(status);
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_record_history_resource ON record_history(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_webhook_events_status ON webhook_events(status);
