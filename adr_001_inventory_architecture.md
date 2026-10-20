# Architecture Decision Record (ADR-001): Enterprise-Grade Inventory Management System

## Status
**ACCEPTED** - Foundation & Architectural Blueprint

---

## 1. Context and Problem Statement
Enterprise inventory systems require absolute data integrity, auditability, and deterministic concurrency control. In concurrent multi-warehouse environments, race conditions can lead to overselling, phantom stock, duplicate goods receipts, and discrepancies between physical inventory and ledger accounting.

The system must handle:
- Multi-location, multi-warehouse operational hierarchies.
- Role-based access control (RBAC) augmented with warehouse-level authorization.
- Strict inventory balance accounting: $\text{Available} = \text{On-Hand} - \text{Reserved}$, where $\text{On-Hand} \ge \text{Reserved} \ge 0$.
- Append-only immutable stock movement ledger: no balance change without an accompanying ledger entry in the exact same database transaction.
- Safe concurrency under simultaneous checkout/dispatch operations: row-level locking (`FOR UPDATE`) with deterministic resource ordering to eliminate deadlocks.
- Purchase order lifecycle with partial receipts.
- Sales order lifecycle with stock reservation and shipment deductions.
- Idempotent API operations with request deduplication.
- Transactional outbox for guaranteed asynchronous event dispatching.

---

## 2. Architectural Decisions

### 2.1 Backend Architecture: Modular Monolith
A modular monolith pattern is adopted with explicit service boundaries to balance strong ACID transaction guarantees with clean domain isolation:
- **Presentation Layer**: FastAPI routers handling HTTP contracts, query parameter parsing, and status mapping.
- **Domain Service Layer**: Pure business logic, state machines, validation rules, stock balance mutations, and transaction coordination.
- **Persistence Layer**: Repository classes executing SQLAlchemy 2.0 async queries, enforcing row-level locks, constraints, and audit logging.
- **Cross-Cutting Concerns**: Correlation IDs, JWT auth with warehouse scope validation, idempotency caching, structured JSON logging, and transactional outbox.

### 2.2 Database Concurrency & Inventory Integrity
1. **Row-Level Locking with Consistent Key Ordering**:
   When an operation touches multiple products in a warehouse, stock level rows are locked via `SELECT ... WHERE warehouse_id = :w AND product_id IN (...) ORDER BY product_id FOR UPDATE`. Sorting by `product_id` prevents circular wait deadlocks between concurrent orders.
2. **Conditional Atomic Updates**:
   Stock deductions execute atomic decrements:
   ```sql
   UPDATE stock_levels
   SET on_hand = on_hand - :qty,
       reserved = reserved - :qty,
       version = version + 1,
       updated_at = NOW()
   WHERE warehouse_id = :wid 
     AND product_id = :pid 
     AND on_hand >= :qty 
     AND reserved >= :qty;
   ```
   If 0 rows are affected, the transaction immediately raises `InsufficientStockException` and rolls back.
3. **Dual-Key Ledger Pairing**:
   Stock balances and movement ledger rows are written synchronously within the same ACID transaction block. No balance update is ever committed without an immutable movement record.
4. **Idempotency Keys**:
   State-changing write endpoints accept an `Idempotency-Key` header stored in the `idempotency_records` table with request hash, response payload, and HTTP status code.

### 2.3 Numbering Strategy for Orders & Movements
Never use `MAX(id) + 1` due to phantom read anomalies under concurrent transactions.
Instead, use an atomic sequence generator table (`document_sequences`) with `SELECT ... FOR UPDATE` incrementing prefix counters (e.g., `PO-202610-0001`, `SO-202610-0001`, `GRN-202610-0001`).

### 2.4 Technology Choices
- **Backend**: Python 3.12+ / FastAPI / SQLAlchemy 2.0 (asyncio) / Pydantic v2 / Alembic / asyncpg / aiosqlite (for test portability).
- **Frontend**: React 18+ / TypeScript / Vite / TanStack Query v5 / TanStack Table v8 / Lucide Icons / Custom Modern Glass & Slate Enterprise Design System with Vanilla CSS tokens.
- **Persistence**: PostgreSQL 16 (authoritative data store) / Redis (caching & task queues).
- **Testing**: Pytest (async integration, concurrency simulation, state machine tests) / Vitest (frontend component & store tests).

---

## 3. Database Schema Blueprint
Entities:
- `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `user_warehouse_access`
- `locations`, `warehouses`
- `product_categories`, `units_of_measure`, `products`
- `customers`, `suppliers`
- `stock_levels` (unique on `(warehouse_id, product_id)`, check constraints `on_hand >= 0`, `reserved >= 0`, `on_hand >= reserved`)
- `stock_movements` (immutable ledger, indexed by `(warehouse_id, product_id, created_at)`)
- `stock_reservations`
- `inventory_transfers`, `inventory_transfer_items`
- `purchase_orders`, `purchase_order_items`, `goods_receipts`, `goods_receipt_items`
- `sales_orders`, `sales_order_items`, `shipments`, `shipment_items`
- `audit_logs`, `idempotency_records`, `outbox_events`, `document_sequences`

---

## 4. Phased Execution Roadmap
- **Phase 0**: Repo layout, configurations, Docker compose, core database session manager, base models, migrations engine.
- **Phase 1**: Authentication, RBAC, warehouse access guards, audit logger, idempotency filter.
- **Phase 2**: Master data APIs (Products, Categories, UOM, Warehouses, Locations, Customers, Suppliers).
- **Phase 3**: Stock Engine (Stock levels, ledger movements, adjustments, transfers, concurrency control).
- **Phase 4**: Purchasing Workflow (PO draft, approve, partial/full goods receipt, GRN numbering).
- **Phase 5**: Sales Workflow (SO draft, confirm with reservation, partial/full shipment, cancellation).
- **Phase 6**: Reporting & Valuation (WAC costing, turnover, low stock alerts, outbox publisher).
- **Phase 7**: Enterprise React UI (Full dashboard, data grids, modals, drawers, status timelines).
- **Phase 8**: Automated Testing (Concurrency stress tests, unit & E2E verification).
