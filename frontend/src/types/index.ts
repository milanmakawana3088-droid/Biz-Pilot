export type UserRole = 'ADMIN' | 'MANAGER' | 'STAFF' | 'AUDITOR';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  assigned_warehouses?: string[];
  created_at: string;
}

export interface Location {
  id: string;
  code: string;
  name: string;
  address_line1?: string;
  city?: string;
  state?: string;
  country: string;
  is_active: boolean;
  created_at: string;
}

export interface Warehouse {
  id: string;
  location_id: string;
  code: string;
  name: string;
  is_active: boolean;
  location?: Location;
  created_at: string;
}

export interface ProductCategory {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
}

export interface Product {
  id: string;
  sku: string;
  barcode?: string;
  name: string;
  description?: string;
  category_id?: string;
  category?: ProductCategory;
  unit_of_measure: string;
  cost_price: number;
  selling_price: number;
  reorder_point: number;
  safety_stock: number;
  is_active: boolean;
  created_at: string;
}

export interface Supplier {
  id: string;
  code: string;
  name: string;
  email?: string;
  phone?: string;
  payment_terms?: string;
  lead_time_days: number;
  is_active: boolean;
  created_at: string;
}

export interface Customer {
  id: string;
  code: string;
  name: string;
  email?: string;
  phone?: string;
  credit_limit: number;
  is_active: boolean;
  created_at: string;
}

export interface StockLevel {
  id: string;
  warehouse_id: string;
  product_id: string;
  on_hand: number;
  reserved: number;
  available: number;
  version: number;
  product?: Product;
  warehouse?: Warehouse;
  updated_at: string;
}

export type MovementType =
  | 'PURCHASE_RECEIPT'
  | 'SALES_SHIPMENT'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT';

export interface StockMovement {
  id: string;
  warehouse_id: string;
  product_id: string;
  movement_type: MovementType;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  balance_before: number;
  balance_after: number;
  reference_type: string;
  reference_id: string;
  reason_code?: string;
  created_by?: string;
  created_at: string;
  product?: Product;
  warehouse?: Warehouse;
}

export interface StockAdjustmentRequest {
  warehouse_id: string;
  product_id: string;
  quantity: number;
  type: 'IN' | 'OUT';
  unit_cost?: number;
  reason_code: string;
}

export interface StockTransferRequest {
  source_warehouse_id: string;
  destination_warehouse_id: string;
  product_id: string;
  quantity: number;
  reason_code?: string;
}

export type POStatus = 'DRAFT' | 'APPROVED' | 'PARTIAL' | 'RECEIVED' | 'CANCELLED';

export interface PurchaseOrderItem {
  id: string;
  purchase_order_id: string;
  product_id: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  line_total: number;
  product?: Product;
}

export interface PurchaseOrder {
  id: string;
  order_number: string;
  warehouse_id: string;
  supplier_id: string;
  status: POStatus;
  order_date: string;
  expected_delivery_date?: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  notes?: string;
  warehouse?: Warehouse;
  supplier?: Supplier;
  items: PurchaseOrderItem[];
  created_at: string;
}

export interface GoodsReceiptItemInput {
  item_id: string;
  quantity_received: number;
  unit_cost?: number;
}

export interface GoodsReceiptCreate {
  warehouse_id: string;
  received_date?: string;
  notes?: string;
  items: GoodsReceiptItemInput[];
}

export type SOStatus = 'DRAFT' | 'CONFIRMED' | 'PARTIAL' | 'SHIPPED' | 'CANCELLED';

export interface SalesOrderItem {
  id: string;
  sales_order_id: string;
  product_id: string;
  quantity_ordered: number;
  quantity_reserved: number;
  quantity_shipped: number;
  unit_price: number;
  line_total: number;
  product?: Product;
}

export interface SalesOrder {
  id: string;
  order_number: string;
  warehouse_id: string;
  customer_id: string;
  status: SOStatus;
  order_date: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  notes?: string;
  warehouse?: Warehouse;
  customer?: Customer;
  items: SalesOrderItem[];
  created_at: string;
}

export interface ShipmentItemInput {
  item_id: string;
  quantity_to_ship: number;
}

export interface ShipmentCreate {
  warehouse_id: string;
  carrier?: string;
  tracking_number?: string;
  shipped_date?: string;
  notes?: string;
  items: ShipmentItemInput[];
}

export interface DashboardKPIs {
  total_products: number;
  total_valuation: number;
  low_stock_count: number;
  open_pos_count: number;
  open_sos_count: number;
  total_warehouses: number;
}

export interface ValuationItem {
  product_id: string;
  sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  on_hand: number;
  reserved: number;
  available: number;
  unit_cost: number;
  total_valuation: number;
}

export interface ReplenishmentItem {
  product_id: string;
  sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  on_hand: number;
  reserved: number;
  available: number;
  reorder_point: number;
  safety_stock: number;
  shortage_quantity: number;
  suggested_order_quantity: number;
}

export interface AuditLog {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id?: string;
  actor_email?: string;
  changes?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
