import {
  AuditLog,
  Customer,
  DashboardKPIs,
  GoodsReceiptCreate,
  Location,
  PaginatedResult,
  Product,
  ProductCategory,
  PurchaseOrder,
  ReplenishmentItem,
  SalesOrder,
  ShipmentCreate,
  StockAdjustmentRequest,
  StockLevel,
  StockMovement,
  StockTransferRequest,
  Supplier,
  User,
  ValuationItem,
  Warehouse,
} from '@/types';

const BASE_URL = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  requireIdempotency: boolean = false
): Promise<T> {
  const token = localStorage.getItem('bizpilot_token');
  const activeWarehouseId = localStorage.getItem('bizpilot_active_warehouse_id');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (activeWarehouseId) {
    headers['X-Warehouse-Id'] = activeWarehouseId;
  }

  if (requireIdempotency && !headers['X-Idempotency-Key']) {
    headers['X-Idempotency-Key'] = generateUUID();
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  const json = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMsg = 'An unexpected error occurred';
    if (json) {
      if (json.error?.message) {
        errorMsg = json.error.message;
        if (json.error.details?.reason) {
          errorMsg += `: ${json.error.details.reason}`;
        }
      } else if (json.detail) {
        errorMsg = typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail);
      } else if (json.message) {
        errorMsg = json.message;
      }
    }
    throw new ApiError(response.status, errorMsg, json);
  }

  // Backend API wraps responses in APIResponse { success: true, data: ... }
  if (json && typeof json === 'object' && 'data' in json && 'success' in json) {
    return json.data as T;
  }

  return json as T;
}

export const api = {
  // Auth
  auth: {
    login: (credentials: { email: string; password: string }) =>
      request<{ access_token: string; refresh_token: string; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    me: () => request<User>('/auth/me'),
    logout: () => request<void>('/auth/logout', { method: 'POST' }),
  },

  // Warehouses & Locations
  warehouses: {
    list: () => request<Warehouse[]>('/warehouses'),
    create: (data: Partial<Warehouse>) =>
      request<Warehouse>('/warehouses', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  locations: {
    list: () => request<Location[]>('/locations'),
    create: (data: Partial<Location>) =>
      request<Location>('/locations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // Products & Categories
  products: {
    list: (params?: { page?: number; size?: number; search?: string; category_id?: string }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      if (params?.search) sp.set('search', params.search);
      if (params?.category_id) sp.set('category_id', params.category_id);
      return request<PaginatedResult<Product>>(`/products?${sp.toString()}`);
    },
    get: (id: string | number) => request<Product>(`/products/${id}`),
    create: (data: Partial<Product>) =>
      request<Product>('/products', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string | number, data: Partial<Product>) =>
      request<Product>(`/products/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    categories: () => request<ProductCategory[]>('/categories'),
    createCategory: (data: { name: string; description?: string }) =>
      request<ProductCategory>('/categories', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    uoms: () => request<any[]>('/units-of-measure'),
  },

  // Suppliers & Customers
  suppliers: {
    list: () => request<Supplier[]>('/suppliers'),
    create: (data: Partial<Supplier>) =>
      request<Supplier>('/suppliers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  customers: {
    list: () => request<Customer[]>('/customers'),
    create: (data: Partial<Customer>) =>
      request<Customer>('/customers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // Inventory Engine
  inventory: {
    getStockLevels: (params?: { warehouse_id?: string; product_id?: string; page?: number; size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.warehouse_id) sp.set('warehouse_id', params.warehouse_id);
      if (params?.product_id) sp.set('product_id', params.product_id);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      return request<PaginatedResult<StockLevel>>(`/inventory/stock-levels?${sp.toString()}`);
    },
    adjustStock: (data: StockAdjustmentRequest) =>
      request<StockLevel>(
        '/inventory/adjustments',
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
        true // Require idempotency key
      ),
    transferStock: (data: StockTransferRequest) =>
      request<any>(
        '/inventory/transfers',
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
        true // Require idempotency key
      ),
    getMovements: (params?: { warehouse_id?: string; product_id?: string; movement_type?: string; page?: number; size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.warehouse_id) sp.set('warehouse_id', params.warehouse_id);
      if (params?.product_id) sp.set('product_id', params.product_id);
      if (params?.movement_type) sp.set('movement_type', params.movement_type);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      return request<PaginatedResult<StockMovement>>(`/inventory/movements?${sp.toString()}`);
    },
  },

  // Purchasing Workflow
  purchasing: {
    listOrders: (params?: { warehouse_id?: string; supplier_id?: string; status?: string; page?: number; size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.warehouse_id) sp.set('warehouse_id', params.warehouse_id);
      if (params?.supplier_id) sp.set('supplier_id', params.supplier_id);
      if (params?.status) sp.set('status', params.status);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      return request<PaginatedResult<PurchaseOrder>>(`/purchasing/orders?${sp.toString()}`);
    },
    getOrder: (id: string | number) => request<PurchaseOrder>(`/purchasing/orders/${id}`),
    createOrder: (data: any) =>
      request<PurchaseOrder>('/purchasing/orders', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    approveOrder: (id: string | number) =>
      request<PurchaseOrder>(`/purchasing/orders/${id}/approve`, {
        method: 'POST',
      }),
    receiveGoods: (id: string | number, data: GoodsReceiptCreate) =>
      request<any>(
        `/purchasing/orders/${id}/receipts`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
        true
      ),
  },

  // Sales Workflow
  sales: {
    listOrders: (params?: { warehouse_id?: string; customer_id?: string; status?: string; page?: number; size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.warehouse_id) sp.set('warehouse_id', params.warehouse_id);
      if (params?.customer_id) sp.set('customer_id', params.customer_id);
      if (params?.status) sp.set('status', params.status);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      return request<PaginatedResult<SalesOrder>>(`/sales/orders?${sp.toString()}`);
    },
    getOrder: (id: string | number) => request<SalesOrder>(`/sales/orders/${id}`),
    createOrder: (data: any) =>
      request<SalesOrder>('/sales/orders', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    confirmOrder: (id: string | number) =>
      request<SalesOrder>(
        `/sales/orders/${id}/confirm`,
        {
          method: 'POST',
        },
        true
      ),
    shipGoods: (id: string | number, data: ShipmentCreate) =>
      request<any>(
        `/sales/orders/${id}/shipments`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
        true
      ),
    cancelOrder: (id: string | number, reason?: string) =>
      request<SalesOrder>(`/sales/orders/${id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
  },

  // Reports
  reports: {
    getDashboard: (warehouseId?: string) => {
      const sp = new URLSearchParams();
      if (warehouseId) sp.set('warehouse_id', warehouseId);
      return request<DashboardKPIs>(`/reporting/dashboard?${sp.toString()}`);
    },
    getValuation: (warehouseId?: string) => {
      const sp = new URLSearchParams();
      if (warehouseId) sp.set('warehouse_id', warehouseId);
      return request<ValuationItem[]>(`/reporting/valuation?${sp.toString()}`);
    },
    getReplenishment: (warehouseId?: string) => {
      const sp = new URLSearchParams();
      if (warehouseId) sp.set('warehouse_id', warehouseId);
      return request<ReplenishmentItem[]>(`/reporting/replenishment?${sp.toString()}`);
    },
  },

  // Audit Logs
  audit: {
    list: (params?: { entity_type?: string; entity_id?: string; page?: number; size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.entity_type) sp.set('entity_type', params.entity_type);
      if (params?.entity_id) sp.set('entity_id', params.entity_id);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.size) sp.set('size', params.size.toString());
      return request<PaginatedResult<AuditLog>>(`/audit/logs?${sp.toString()}`);
    },
  },
};
