from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.core.exceptions import BusinessRuleViolationError, ResourceNotFoundError
from app.models.enterprise import Customer, OrderLineItem, Payment, Product, SalesOrder, WorkTask
from app.repositories.enterprise_repository import EnterpriseRepository
from app.schemas.business import OrderCreate, PaymentCreate, ReportCreate


class BusinessService:
    def __init__(self, enterprise_repository: EnterpriseRepository) -> None:
        self.enterprise = enterprise_repository

    def create_order(self, payload: OrderCreate, *, actor_id: UUID | None) -> SalesOrder:
        customer = self._require_not_deleted(
            self.enterprise.customers.get(payload.customer_id),
            "Customer",
        )
        order = self.enterprise.orders.create(
            {
                "order_number": payload.order_number or f"ORD-{uuid4().hex[:10].upper()}",
                "customer_id": customer.id,
                "status": "confirmed",
                "total_amount": Decimal("0.00"),
                "notes": payload.notes,
            }
        )

        total = Decimal("0.00")
        for line in payload.line_items:
            product = self._require_not_deleted(
                self.enterprise.products.get(line.product_id),
                "Product",
            )
            if product.status != "active":
                raise BusinessRuleViolationError(f"Product {product.sku} is not active")
            if product.stock_quantity < line.quantity:
                raise BusinessRuleViolationError(f"Insufficient stock for {product.sku}")

            line_total = Decimal(product.unit_price) * Decimal(line.quantity)
            self.enterprise.order_line_items.create(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "quantity": line.quantity,
                    "unit_price": product.unit_price,
                    "line_total": line_total,
                }
            )
            product.stock_quantity -= line.quantity
            product.updated_at = self._now()
            total += line_total

        order.total_amount = total
        self.enterprise.create_audit_log(
            actor_id=actor_id,
            action="CREATE_ORDER",
            resource_type="order",
            resource_id=str(order.id),
        )
        self.enterprise.create_notification(
            user_id=actor_id,
            title="Order created",
            message=f"Order {order.order_number} was created.",
            category="orders",
        )
        return order

    def create_payment(self, payload: PaymentCreate, *, actor_id: UUID | None) -> Payment:
        order = self._require_not_deleted(self.enterprise.orders.get(payload.order_id), "Order")
        if order.status == "cancelled":
            raise BusinessRuleViolationError("Cannot pay a cancelled order")

        paid_total = Decimal(
            self.enterprise.session.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.order_id == order.id,
                    Payment.status == "completed",
                )
            )
        )
        outstanding = Decimal(order.total_amount) - paid_total
        if payload.amount > outstanding:
            raise BusinessRuleViolationError("Payment amount exceeds outstanding balance")

        payment = self.enterprise.payments.create(
            {
                "order_id": order.id,
                "customer_id": order.customer_id,
                "amount": payload.amount,
                "method": payload.method,
                "status": "completed",
                "transaction_reference": payload.transaction_reference,
            }
        )
        if payload.amount == outstanding:
            order.status = "paid"
            order.updated_at = self._now()

        self.enterprise.create_audit_log(
            actor_id=actor_id,
            action="CREATE_PAYMENT",
            resource_type="payment",
            resource_id=str(payment.id),
        )
        return payment

    def complete_task(self, task_id: UUID, *, actor_id: UUID | None) -> WorkTask:
        task = self._require_not_deleted(self.enterprise.tasks.get(task_id), "Task")
        if task.status == "completed":
            return task
        task.status = "completed"
        task.completed_at = self._now()
        task.updated_at = self._now()
        self.enterprise.create_audit_log(
            actor_id=actor_id,
            action="COMPLETE_TASK",
            resource_type="task",
            resource_id=str(task.id),
        )
        return task

    def generate_report(self, payload: ReportCreate, *, actor_id: UUID | None):
        report = self.enterprise.reports.create(
            {
                "name": payload.name,
                "report_type": payload.report_type,
                "filters": payload.filters,
                "generated_by_id": actor_id,
                "status": "completed",
                "result": self._build_report_result(payload.report_type),
            }
        )
        self.enterprise.create_audit_log(
            actor_id=actor_id,
            action="GENERATE_REPORT",
            resource_type="report",
            resource_id=str(report.id),
        )
        return report

    def _build_report_result(self, report_type: str) -> dict[str, Any]:
        if report_type == "sales_summary":
            return {
                "orders": self.enterprise.orders.count(),
                "revenue": str(
                    self.enterprise.session.scalar(
                        select(func.coalesce(func.sum(Payment.amount), 0)).where(
                            Payment.status == "completed"
                        )
                    )
                ),
                "payments": self.enterprise.payments.count(
                    filters=(Payment.status == "completed",)
                ),
            }
        if report_type == "customer_summary":
            return {
                "customers": self.enterprise.customers.count(
                    filters=(Customer.deleted_at.is_(None),)
                )
            }
        if report_type == "task_summary":
            return {
                "open": self.enterprise.tasks.count(
                    filters=(
                        WorkTask.deleted_at.is_(None),
                        WorkTask.status != "completed",
                    )
                ),
                "completed": self.enterprise.tasks.count(
                    filters=(WorkTask.status == "completed",)
                ),
            }
        if report_type == "inventory_summary":
            return {
                "products": self.enterprise.products.count(
                    filters=(Product.deleted_at.is_(None),)
                ),
                "stock_units": self.enterprise.session.scalar(
                    select(func.coalesce(func.sum(Product.stock_quantity), 0))
                ),
            }
        return {}

    def _require_not_deleted(self, instance: Any | None, label: str) -> Any:
        if instance is None or getattr(instance, "deleted_at", None) is not None:
            raise ResourceNotFoundError(f"{label} not found")
        return instance

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
