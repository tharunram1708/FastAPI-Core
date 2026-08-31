from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class Permission(StrEnum):
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"
    READ_USER = "READ_USER"
    CREATE_ITEM = "CREATE_ITEM"
    UPDATE_ITEM = "UPDATE_ITEM"
    DELETE_ITEM = "DELETE_ITEM"
    READ_ITEM = "READ_ITEM"
    MANAGE_FILES = "MANAGE_FILES"
    IMPORT_CSV = "IMPORT_CSV"
    EXPORT_CSV = "EXPORT_CSV"
    MANAGE_WEBHOOKS = "MANAGE_WEBHOOKS"
    VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"
    BULK_OPERATIONS = "BULK_OPERATIONS"
    MANAGE_EMPLOYEES = "MANAGE_EMPLOYEES"
    MANAGE_CUSTOMERS = "MANAGE_CUSTOMERS"
    MANAGE_PRODUCTS = "MANAGE_PRODUCTS"
    MANAGE_ORDERS = "MANAGE_ORDERS"
    MANAGE_PAYMENTS = "MANAGE_PAYMENTS"
    MANAGE_TASKS = "MANAGE_TASKS"
    VIEW_REPORTS = "VIEW_REPORTS"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {permission.value for permission in Permission},
    Role.MANAGER.value: {
        Permission.READ_USER.value,
        Permission.CREATE_ITEM.value,
        Permission.UPDATE_ITEM.value,
        Permission.DELETE_ITEM.value,
        Permission.READ_ITEM.value,
        Permission.MANAGE_FILES.value,
        Permission.IMPORT_CSV.value,
        Permission.EXPORT_CSV.value,
        Permission.BULK_OPERATIONS.value,
        Permission.MANAGE_EMPLOYEES.value,
        Permission.MANAGE_CUSTOMERS.value,
        Permission.MANAGE_PRODUCTS.value,
        Permission.MANAGE_ORDERS.value,
        Permission.MANAGE_PAYMENTS.value,
        Permission.MANAGE_TASKS.value,
        Permission.VIEW_REPORTS.value,
    },
    Role.USER.value: {
        Permission.READ_ITEM.value,
        Permission.EXPORT_CSV.value,
        Permission.MANAGE_TASKS.value,
        Permission.VIEW_REPORTS.value,
    },
}


def normalize_role(role: str) -> str:
    normalized = role.strip().upper()
    if normalized not in ROLE_PERMISSIONS:
        raise ValueError("unsupported role")
    return normalized


def effective_permissions(role: str, explicit_permissions: list[str] | None = None) -> set[str]:
    permissions = set(ROLE_PERMISSIONS.get(role.upper(), set()))
    permissions.update(explicit_permissions or [])
    return permissions
