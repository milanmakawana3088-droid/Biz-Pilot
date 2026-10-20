from enum import Enum
from typing import Dict, List, Set


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER"
    PURCHASER = "PURCHASER"
    SALES = "SALES"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    # User & RBAC
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    ROLE_MANAGE = "role:manage"

    # Master Data
    PRODUCT_READ = "product:read"
    PRODUCT_WRITE = "product:write"
    PRODUCT_DELETE = "product:delete"

    WAREHOUSE_READ = "warehouse:read"
    WAREHOUSE_WRITE = "warehouse:write"

    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"

    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"

    # Inventory
    STOCK_READ = "stock:read"
    STOCK_ADJUST = "stock:adjust"
    STOCK_TRANSFER = "stock:transfer"

    # Purchasing
    PO_READ = "po:read"
    PO_WRITE = "po:write"
    PO_APPROVE = "po:approve"
    PO_RECEIVE = "po:receive"
    PO_CANCEL = "po:cancel"

    # Sales
    SO_READ = "so:read"
    SO_WRITE = "so:write"
    SO_CONFIRM = "so:confirm"
    SO_SHIP = "so:ship"
    SO_CANCEL = "so:cancel"

    # Reporting & Audit
    REPORT_READ = "report:read"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS_MAP: Dict[RoleEnum, Set[Permission]] = {
    RoleEnum.ADMIN: set(Permission),  # All permissions
    RoleEnum.WAREHOUSE_MANAGER: {
        Permission.PRODUCT_READ,
        Permission.WAREHOUSE_READ,
        Permission.STOCK_READ,
        Permission.STOCK_ADJUST,
        Permission.STOCK_TRANSFER,
        Permission.PO_READ,
        Permission.PO_RECEIVE,
        Permission.SO_READ,
        Permission.SO_SHIP,
        Permission.REPORT_READ,
        Permission.AUDIT_READ,
    },
    RoleEnum.PURCHASER: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_WRITE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_WRITE,
        Permission.WAREHOUSE_READ,
        Permission.STOCK_READ,
        Permission.PO_READ,
        Permission.PO_WRITE,
        Permission.PO_APPROVE,
        Permission.PO_CANCEL,
        Permission.REPORT_READ,
    },
    RoleEnum.SALES: {
        Permission.PRODUCT_READ,
        Permission.CUSTOMER_READ,
        Permission.CUSTOMER_WRITE,
        Permission.WAREHOUSE_READ,
        Permission.STOCK_READ,
        Permission.SO_READ,
        Permission.SO_WRITE,
        Permission.SO_CONFIRM,
        Permission.SO_CANCEL,
        Permission.REPORT_READ,
    },
    RoleEnum.VIEWER: {
        Permission.PRODUCT_READ,
        Permission.WAREHOUSE_READ,
        Permission.CUSTOMER_READ,
        Permission.SUPPLIER_READ,
        Permission.STOCK_READ,
        Permission.PO_READ,
        Permission.SO_READ,
        Permission.REPORT_READ,
    },
}
