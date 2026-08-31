from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.core.exceptions import ResourceNotFoundError
from app.models.enterprise import Customer, OrderLineItem, Payment, Product, SalesOrder, WorkTask
from app.schemas.business import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    OrderCreate,
    OrderLineRead,
    OrderRead,
    OrderUpdate,
    PaymentCreate,
    PaymentRead,
    PaymentUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ReportCreate,
    ReportRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)


router = APIRouter()


def _snapshot(model: Any, schema: type) -> dict[str, Any]:
    return schema.model_validate(model).model_dump(mode="json")


def _update_model(instance: Any, data: dict[str, Any]) -> Any:
    for key, value in data.items():
        setattr(instance, key, value)
    instance.updated_at = datetime.now(timezone.utc)
    return instance


def _not_deleted(instance: Any | None, label: str) -> Any:
    if instance is None or getattr(instance, "deleted_at", None) is not None:
        raise ResourceNotFoundError(f"{label} not found")
    return instance


def _order_read(db: DatabaseSessionDep, order: SalesOrder) -> OrderRead:
    lines = list(
        db.enterprise.session.scalars(
            select(OrderLineItem).where(OrderLineItem.order_id == order.id)
        )
    )
    return OrderRead.model_validate(order).model_copy(
        update={"line_items": [OrderLineRead.model_validate(line) for line in lines]}
    )


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED, summary="Create employee")
async def create_employee(
    payload: EmployeeCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_EMPLOYEES))],
) -> EmployeeRead:
    employee = db.enterprise.employees.create(payload.model_dump(mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="CREATE_EMPLOYEE", resource_type="employee", resource_id=str(employee.id))
    return employee


@router.get("/employees", response_model=list[EmployeeRead], summary="List employees")
async def list_employees(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_EMPLOYEES))],
    q: str | None = None,
    department: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[EmployeeRead]:
    model = db.enterprise.employees.model
    filters = [model.deleted_at.is_(None)]
    if q:
        pattern = f"%{q.casefold()}%"
        filters.append(func.lower(model.first_name + " " + model.last_name).like(pattern))
    if department:
        filters.append(model.department == department)
    if status_filter:
        filters.append(model.status == status_filter)
    return db.enterprise.employees.list(filters=filters, order_by=(model.created_at.desc(),), skip=skip, limit=limit)


@router.get("/employees/{employee_id}", response_model=EmployeeRead, summary="Get employee")
async def get_employee(
    employee_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_EMPLOYEES))],
) -> EmployeeRead:
    return _not_deleted(db.enterprise.employees.get(employee_id), "Employee")


@router.patch("/employees/{employee_id}", response_model=EmployeeRead, summary="Update employee")
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_EMPLOYEES))],
) -> EmployeeRead:
    employee = _not_deleted(db.enterprise.employees.get(employee_id), "Employee")
    db.enterprise.create_history(resource_type="employee", resource_id=str(employee.id), previous_data=_snapshot(employee, EmployeeRead), changed_by_id=actor.id)
    _update_model(employee, payload.model_dump(exclude_unset=True, mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_EMPLOYEE", resource_type="employee", resource_id=str(employee.id))
    return employee


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete employee")
async def delete_employee(
    employee_id: UUID,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_EMPLOYEES))],
) -> Response:
    employee = _not_deleted(db.enterprise.employees.get(employee_id), "Employee")
    db.enterprise.employees.soft_delete(employee)
    db.enterprise.create_audit_log(actor_id=actor.id, action="DELETE_EMPLOYEE", resource_type="employee", resource_id=str(employee.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED, summary="Create customer")
async def create_customer(
    payload: CustomerCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_CUSTOMERS))],
) -> CustomerRead:
    customer = db.enterprise.customers.create(payload.model_dump(mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="CREATE_CUSTOMER", resource_type="customer", resource_id=str(customer.id))
    return customer


@router.get("/customers", response_model=list[CustomerRead], summary="List customers")
async def list_customers(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_CUSTOMERS))],
    q: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CustomerRead]:
    filters = [Customer.deleted_at.is_(None)]
    if q:
        pattern = f"%{q.casefold()}%"
        filters.append(func.lower(Customer.name).like(pattern))
    if status_filter:
        filters.append(Customer.status == status_filter)
    return db.enterprise.customers.list(filters=filters, order_by=(Customer.created_at.desc(),), skip=skip, limit=limit)


@router.get("/customers/{customer_id}", response_model=CustomerRead, summary="Get customer")
async def get_customer(
    customer_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_CUSTOMERS))],
) -> CustomerRead:
    return _not_deleted(db.enterprise.customers.get(customer_id), "Customer")


@router.patch("/customers/{customer_id}", response_model=CustomerRead, summary="Update customer")
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_CUSTOMERS))],
) -> CustomerRead:
    customer = _not_deleted(db.enterprise.customers.get(customer_id), "Customer")
    db.enterprise.create_history(resource_type="customer", resource_id=str(customer.id), previous_data=_snapshot(customer, CustomerRead), changed_by_id=actor.id)
    _update_model(customer, payload.model_dump(exclude_unset=True, mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_CUSTOMER", resource_type="customer", resource_id=str(customer.id))
    return customer


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete customer")
async def delete_customer(
    customer_id: UUID,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_CUSTOMERS))],
) -> Response:
    customer = _not_deleted(db.enterprise.customers.get(customer_id), "Customer")
    db.enterprise.customers.soft_delete(customer)
    db.enterprise.create_audit_log(actor_id=actor.id, action="DELETE_CUSTOMER", resource_type="customer", resource_id=str(customer.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, summary="Create product")
async def create_product(
    payload: ProductCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PRODUCTS))],
) -> ProductRead:
    product = db.enterprise.products.create(payload.model_dump(mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="CREATE_PRODUCT", resource_type="product", resource_id=str(product.id))
    return product


@router.get("/products", response_model=list[ProductRead], summary="List products")
async def list_products(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PRODUCTS))],
    q: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ProductRead]:
    filters = [Product.deleted_at.is_(None)]
    if q:
        pattern = f"%{q.casefold()}%"
        filters.append(func.lower(Product.name).like(pattern))
    if category:
        filters.append(Product.category == category)
    if status_filter:
        filters.append(Product.status == status_filter)
    return db.enterprise.products.list(filters=filters, order_by=(Product.created_at.desc(),), skip=skip, limit=limit)


@router.get("/products/{product_id}", response_model=ProductRead, summary="Get product")
async def get_product(
    product_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PRODUCTS))],
) -> ProductRead:
    return _not_deleted(db.enterprise.products.get(product_id), "Product")


@router.patch("/products/{product_id}", response_model=ProductRead, summary="Update product")
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PRODUCTS))],
) -> ProductRead:
    product = _not_deleted(db.enterprise.products.get(product_id), "Product")
    db.enterprise.create_history(resource_type="product", resource_id=str(product.id), previous_data=_snapshot(product, ProductRead), changed_by_id=actor.id)
    _update_model(product, payload.model_dump(exclude_unset=True, mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_PRODUCT", resource_type="product", resource_id=str(product.id))
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete product")
async def delete_product(
    product_id: UUID,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PRODUCTS))],
) -> Response:
    product = _not_deleted(db.enterprise.products.get(product_id), "Product")
    db.enterprise.products.soft_delete(product)
    db.enterprise.create_audit_log(actor_id=actor.id, action="DELETE_PRODUCT", resource_type="product", resource_id=str(product.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED, summary="Create order")
async def create_order(
    payload: OrderCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_ORDERS))],
) -> OrderRead:
    order = db.business.create_order(payload, actor_id=actor.id)
    return _order_read(db, order)


@router.get("/orders", response_model=list[OrderRead], summary="List orders")
async def list_orders(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_ORDERS))],
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[OrderRead]:
    filters = [SalesOrder.deleted_at.is_(None)]
    if customer_id:
        filters.append(SalesOrder.customer_id == customer_id)
    if status_filter:
        filters.append(SalesOrder.status == status_filter)
    orders = db.enterprise.orders.list(filters=filters, order_by=(SalesOrder.created_at.desc(),), skip=skip, limit=limit)
    return [_order_read(db, order) for order in orders]


@router.get("/orders/{order_id}", response_model=OrderRead, summary="Get order")
async def get_order(
    order_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_ORDERS))],
) -> OrderRead:
    return _order_read(db, _not_deleted(db.enterprise.orders.get(order_id), "Order"))


@router.patch("/orders/{order_id}", response_model=OrderRead, summary="Update order")
async def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_ORDERS))],
) -> OrderRead:
    order = _not_deleted(db.enterprise.orders.get(order_id), "Order")
    db.enterprise.create_history(resource_type="order", resource_id=str(order.id), previous_data=_snapshot(_order_read(db, order), OrderRead), changed_by_id=actor.id)
    _update_model(order, payload.model_dump(exclude_unset=True, mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_ORDER", resource_type="order", resource_id=str(order.id))
    return _order_read(db, order)


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, summary="Create payment")
async def create_payment(
    payload: PaymentCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PAYMENTS))],
) -> PaymentRead:
    return db.business.create_payment(payload, actor_id=actor.id)


@router.get("/payments", response_model=list[PaymentRead], summary="List payments")
async def list_payments(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PAYMENTS))],
    order_id: UUID | None = None,
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PaymentRead]:
    filters = []
    if order_id:
        filters.append(Payment.order_id == order_id)
    if customer_id:
        filters.append(Payment.customer_id == customer_id)
    if status_filter:
        filters.append(Payment.status == status_filter)
    return db.enterprise.payments.list(filters=filters, order_by=(Payment.created_at.desc(),), skip=skip, limit=limit)


@router.patch("/payments/{payment_id}", response_model=PaymentRead, summary="Update payment")
async def update_payment(
    payment_id: UUID,
    payload: PaymentUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PAYMENTS))],
) -> PaymentRead:
    payment = db.enterprise.payments.get(payment_id)
    if payment is None:
        raise ResourceNotFoundError("Payment not found")
    _update_model(payment, payload.model_dump(mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_PAYMENT", resource_type="payment", resource_id=str(payment.id))
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentRead, summary="Get payment")
async def get_payment(
    payment_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_PAYMENTS))],
) -> PaymentRead:
    payment = db.enterprise.payments.get(payment_id)
    if payment is None:
        raise ResourceNotFoundError("Payment not found")
    return payment


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED, summary="Create task")
async def create_task(
    payload: TaskCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
) -> TaskRead:
    task = db.enterprise.tasks.create(payload.model_dump(mode="python"))
    db.enterprise.create_audit_log(actor_id=actor.id, action="CREATE_TASK", resource_type="task", resource_id=str(task.id))
    return task


@router.get("/tasks", response_model=list[TaskRead], summary="List tasks")
async def list_tasks(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
    status_filter: str | None = None,
    assigned_to_user_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TaskRead]:
    filters = [WorkTask.deleted_at.is_(None)]
    if status_filter:
        filters.append(WorkTask.status == status_filter)
    if assigned_to_user_id:
        filters.append(WorkTask.assigned_to_user_id == assigned_to_user_id)
    return db.enterprise.tasks.list(filters=filters, order_by=(WorkTask.created_at.desc(),), skip=skip, limit=limit)


@router.get("/tasks/{task_id}", response_model=TaskRead, summary="Get task")
async def get_task(
    task_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
) -> TaskRead:
    return _not_deleted(db.enterprise.tasks.get(task_id), "Task")


@router.patch("/tasks/{task_id}", response_model=TaskRead, summary="Update task")
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
) -> TaskRead:
    task = _not_deleted(db.enterprise.tasks.get(task_id), "Task")
    db.enterprise.create_history(resource_type="task", resource_id=str(task.id), previous_data=_snapshot(task, TaskRead), changed_by_id=actor.id)
    data = payload.model_dump(exclude_unset=True, mode="python")
    if data.get("status") == "completed" and task.completed_at is None:
        data["completed_at"] = datetime.now(timezone.utc)
    _update_model(task, data)
    db.enterprise.create_audit_log(actor_id=actor.id, action="UPDATE_TASK", resource_type="task", resource_id=str(task.id))
    return task


@router.post("/tasks/{task_id}/complete", response_model=TaskRead, summary="Complete task")
async def complete_task(
    task_id: UUID,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
) -> TaskRead:
    return db.business.complete_task(task_id, actor_id=actor.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete task")
async def delete_task(
    task_id: UUID,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_TASKS))],
) -> Response:
    task = _not_deleted(db.enterprise.tasks.get(task_id), "Task")
    db.enterprise.tasks.soft_delete(task)
    db.enterprise.create_audit_log(actor_id=actor.id, action="DELETE_TASK", resource_type="task", resource_id=str(task.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reports", response_model=ReportRead, status_code=status.HTTP_201_CREATED, summary="Generate report")
async def generate_report(
    payload: ReportCreate,
    db: DatabaseSessionDep,
    actor: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.VIEW_REPORTS))],
) -> ReportRead:
    return db.business.generate_report(payload, actor_id=actor.id)


@router.get("/reports", response_model=list[ReportRead], summary="List reports")
async def list_reports(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.VIEW_REPORTS))],
    report_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ReportRead]:
    model = db.enterprise.reports.model
    filters = [model.report_type == report_type] if report_type else []
    return db.enterprise.reports.list(filters=filters, order_by=(model.created_at.desc(),), skip=skip, limit=limit)


@router.get("/reports/{report_id}", response_model=ReportRead, summary="Get report")
async def get_report(
    report_id: UUID,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.VIEW_REPORTS))],
) -> ReportRead:
    report = db.enterprise.reports.get(report_id)
    if report is None:
        raise ResourceNotFoundError("Report not found")
    return report

