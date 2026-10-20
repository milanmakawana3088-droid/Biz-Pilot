from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel


class WarehouseValuation(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    total_items: int
    total_on_hand: int
    total_reserved: int
    total_valuation: Decimal


class DashboardMetricsResponse(BaseModel):
    total_products: int
    total_warehouses: int
    total_customers: int
    total_suppliers: int
    total_on_hand_units: int
    total_reserved_units: int
    low_stock_alerts_count: int
    total_inventory_valuation: Decimal
    total_open_purchase_orders: int
    total_open_sales_orders: int
    warehouse_breakdown: List[WarehouseValuation]


class LowStockAlert(BaseModel):
    product_id: int
    sku: str
    name: str
    category_name: Optional[str] = None
    warehouse_id: int
    warehouse_code: str
    on_hand: int
    reorder_level: int
    deficit: int
