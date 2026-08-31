from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _user_payload() -> dict:
    name = f"user_{uuid4().hex[:8]}"
    return {
        "username": name,
        "email": f"{name}@example.com",
        "password": "Password123!",
    }


def test_register_login_me_and_logout_all() -> None:
    payload = _user_payload()
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]

    logout = client.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    rejected = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rejected.status_code == 401


def test_password_reset_simulated_otp_flow() -> None:
    payload = _user_payload()
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
    assert forgot.status_code == 200
    body = forgot.json()
    assert body["reset_token"]
    assert body["otp"]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": body["reset_token"],
            "otp": body["otp"],
            "new_password": "NewPassword123!",
        },
    )
    assert reset.status_code == 204


def test_api_key_item_write_and_readiness() -> None:
    item_name = f"Desk {uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/items",
        headers={"X-API-Key": "dev-secret-key"},
        json={"name": item_name, "category": "office", "inventory_count": 2},
    )
    assert created.status_code == 201
    assert created.json()["name"] == item_name

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"


def test_webhook_failure_and_openapi_paths() -> None:
    failed = client.post(
        "/api/v1/webhooks",
        json={
            "source": "unit-test",
            "event_type": "demo.failed",
            "payload": {"force_fail": True},
        },
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/documents" in schema.json()["paths"]
    assert "/api/v1/search/items" in schema.json()["paths"]


def test_business_management_workflow() -> None:
    headers = {"X-API-Key": "dev-secret-key"}
    suffix = uuid4().hex[:8]

    employee = client.post(
        "/api/v1/business/employees",
        headers=headers,
        json={
            "employee_code": f"EMP-{suffix}",
            "first_name": "Asha",
            "last_name": "Rao",
            "email": f"asha-{suffix}@example.com",
            "department": "sales",
            "title": "Account Manager",
            "salary": "75000.00",
        },
    )
    assert employee.status_code == 201

    customer = client.post(
        "/api/v1/business/customers",
        headers=headers,
        json={"name": f"Acme {suffix}", "email": f"acme-{suffix}@example.com"},
    )
    assert customer.status_code == 201

    product = client.post(
        "/api/v1/business/products",
        headers=headers,
        json={
            "sku": f"SKU-{suffix}",
            "name": f"Widget {suffix}",
            "category": "hardware",
            "unit_price": "25.50",
            "stock_quantity": 10,
        },
    )
    assert product.status_code == 201

    order = client.post(
        "/api/v1/business/orders",
        headers=headers,
        json={
            "customer_id": customer.json()["id"],
            "line_items": [{"product_id": product.json()["id"], "quantity": 2}],
        },
    )
    assert order.status_code == 201
    assert order.json()["total_amount"] == "51.00"

    payment = client.post(
        "/api/v1/business/payments",
        headers=headers,
        json={
            "order_id": order.json()["id"],
            "amount": "51.00",
            "method": "card",
            "transaction_reference": f"TXN-{suffix}",
        },
    )
    assert payment.status_code == 201
    assert payment.json()["status"] == "completed"

    task = client.post(
        "/api/v1/business/tasks",
        headers=headers,
        json={
            "title": f"Follow up {suffix}",
            "employee_id": employee.json()["id"],
            "customer_id": customer.json()["id"],
            "priority": "high",
        },
    )
    assert task.status_code == 201

    complete = client.post(
        f"/api/v1/business/tasks/{task.json()['id']}/complete",
        headers=headers,
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"

    report = client.post(
        "/api/v1/business/reports",
        headers=headers,
        json={"name": f"Sales {suffix}", "report_type": "sales_summary"},
    )
    assert report.status_code == 201
    assert "revenue" in report.json()["result"]


def test_order_rejects_insufficient_stock() -> None:
    headers = {"X-API-Key": "dev-secret-key"}
    suffix = uuid4().hex[:8]

    customer = client.post(
        "/api/v1/business/customers",
        headers=headers,
        json={"name": f"Stock Test {suffix}", "email": f"stock-{suffix}@example.com"},
    )
    assert customer.status_code == 201

    product = client.post(
        "/api/v1/business/products",
        headers=headers,
        json={
            "sku": f"LOW-{suffix}",
            "name": f"Limited Widget {suffix}",
            "category": "hardware",
            "unit_price": "10.00",
            "stock_quantity": 1,
        },
    )
    assert product.status_code == 201

    order = client.post(
        "/api/v1/business/orders",
        headers=headers,
        json={
            "customer_id": customer.json()["id"],
            "line_items": [{"product_id": product.json()["id"], "quantity": 2}],
        },
    )
    assert order.status_code == 409
    assert order.json()["error_code"] == "BUSINESS_RULE_VIOLATION"
