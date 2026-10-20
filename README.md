# BizPilot — Enterprise-Grade Inventory Management System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-d71f00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18.3-61dafb?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646cff?logo=vite&logoColor=white)](https://vitejs.dev/)

BizPilot is an enterprise-grade multi-location inventory and warehouse management system designed for high concurrency, strict audit compliance, and large-scale operational throughput.

---

## 1. System Architecture & Engineering Principles

BizPilot enforces strict relational invariants, deterministic concurrency controls, and idempotent execution paths.

```
                    ┌─────────────────────────┐
                    │    React 18 + Vite UI   │
                    │ (Vanilla CSS Tokens, TS)│
                    └────────────┬────────────┘
                                 │ HTTP / JSON
                                 ▼
                    ┌─────────────────────────┐
                    │  FastAPI REST Gateway   │
                    │ ├ Idempotency Check     │
                    │ ├ Correlation & RBAC    │
                    │ └ Warehouse Scoping     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌─────────────────────────────────┐        ┌───────────────────────────┐
│       PostgreSQL 16 Engine      │        │       Redis 7 Cache       │
│ ├ Ordered SELECT FOR UPDATE     │        │ ├ Idempotency Keys (TTL)  │
│ ├ Dual-Write Append-Only Ledger │        │ └ Celery Broker / Results │
│ ├ Monotonic Sequence Generator  │        └─────────────┬─────────────┘
│ └ Transactional Outbox Pattern  │                      │
└─────────────────────────────────┘                      ▼
                                           ┌───────────────────────────┐
                                           │    Celery Async Worker    │
                                           │ (Outbox event dispatcher) │
                                           └───────────────────────────┘
```

### Critical Architectural Decisions

1. **Deadlock-Free Deterministic Concurrency (`SELECT ... FOR UPDATE`)**:
   - Stock balance records (`stock_levels`) are locked using pessimistic locking.
   - When multiple SKUs are modified within a single transaction (e.g. multi-item sales shipments or transfers), `product_id`s are sorted in strict ascending order before locking, mathematically eliminating deadlocks.
2. **Dual-Write Append-Only Immutable Stock Movement Ledger**:
   - Any mutation to physical stock (`on_hand`, `reserved`, or `available`) **must** write a corresponding entry to `stock_movements` within the exact same database transaction.
   - Balance changes without a movement record or orphaned movements are structurally impossible.
   - Movement ledger rows are append-only and immutable.
3. **Strict Stock Mathematical Invariant**:
   $$\text{Available Stock} = \text{On-Hand} - \text{Reserved}$$
   $$\text{On-Hand} \ge 0, \quad \text{Reserved} \ge 0, \quad \text{Available} \ge 0$$
   - Enforced both through database CHECK constraints and application-level pre-validation.
4. **Concurrency-Safe Monotonic Number Sequences**:
   - High-concurrency operations never rely on `MAX(id) + 1` or uncommitted sequences.
   - A dedicated `sequence_generators` table uses atomic row-level increments (`FOR UPDATE`) partitioned by prefix and month (`PO-202610-0001`, `SO-202610-0001`, `GRN-202610-0001`, `SHP-202610-0001`, `TR-202610-0001`, `ADJ-202610-0001`).
5. **Idempotency Protection for Stock Mutations**:
   - All state-altering operations accept an optional or mandatory `X-Idempotency-Key` HTTP header.
   - Cached responses in Redis prevent network retries or double clicks from executing duplicate stock deductions.

---

## 2. Core Business Workflows

### Purchase Order Lifecycle
$$\text{Draft} \longrightarrow \text{Approved} \longrightarrow \text{Partial Receipt} \longrightarrow \text{Fully Received}$$
- **Draft**: Buyers create multi-item purchase orders against registered suppliers.
- **Approval**: Authorized managers approve the order.
- **Goods Receipt (GRN)**: Warehouse dock personnel physically inspect items and record received quantities. Partial receipts are natively supported. Each GRN increments `on_hand` and generates `PURCHASE_RECEIPT` movement records.

### Sales Order Lifecycle
$$\text{Draft} \longrightarrow \text{Confirmed (Stock Reserved)} \longrightarrow \text{Partial Shipment} \longrightarrow \text{Shipped}$$
- **Draft**: Sales representatives enter orders for customers.
- **Confirmation**: Atomically locks and checks stock across all order items. If sufficient available stock exists, increases `reserved` balance. If insufficient stock, rolls back and returns precise shortage details.
- **Shipment Dispatch**: Logistics records carrier and tracking number. Atomically decrements both `reserved` and `on_hand` stock, and generates `SALES_SHIPMENT` movement records.
- **Cancellation**: If a confirmed order is cancelled, all reserved quantities are released back to available stock.

### Multi-Facility Topology & Inventory Rebalancing
- Supports multiple physical locations and distinct warehouses.
- Users can be restricted to specific assigned warehouses or granted global access.
- Inter-warehouse transfers atomically decrement stock at the source facility and increment stock at the destination facility in a single transaction.

---

## 3. Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.12 / 3.14 compatible)
- **ORM**: SQLAlchemy 2.0 (Strict Async IO with `asyncpg` for PostgreSQL and `aiosqlite` for local dev/testing)
- **Migrations**: Alembic
- **Validation**: Pydantic v2 (`ConfigDict(from_attributes=True)`)
- **Security**: OAuth2 Bearer JWT (`pyjwt`), password hashing with `bcrypt`
- **Background Tasks**: Celery 5.4 + Redis 7 (Transactional outbox pattern)

### Frontend
- **Framework**: React 18.3 + TypeScript + Vite
- **Styling**: Vanilla CSS custom design system (Deep Slate theme, glassmorphism, responsive tables, modals, badges — no Tailwind CSS dependency)
- **State & Caching**: `@tanstack/react-query`
- **Routing**: `react-router-dom` v6
- **Icons**: `lucide-react`

---

## 4. Quick Start with Docker Compose

To launch PostgreSQL 16, Redis 7, Celery Worker, FastAPI backend, and Nginx frontend in a unified container network:

```bash
# 1. Clone repository and copy environment configuration
cp .env.example .env

# 2. Build and run all services
docker compose up --build -d

# 3. View running containers
docker compose ps
```

The system will be available at:
- **Frontend Portal**: `http://localhost`
- **Backend API Docs (Swagger UI)**: `http://localhost:8000/api/v1/docs`
- **Health Check**: `http://localhost:8000/health`

---

## 5. Local Development Setup

### Backend Local Run

```bash
cd backend

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations (or SQLite auto-init on boot)
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Local Run

```bash
cd frontend

# Install node dependencies
npm install

# Start Vite dev server with proxy to backend
npm run dev
```

The Vite dev server starts at `http://localhost:5173` with automatic API proxying to `http://127.0.0.1:8000`.

---

## 6. Pre-Configured Demo Accounts

Upon initial startup, BizPilot seeds standard reference data (warehouses, product categories, sample SKUs, units of measure) and default user accounts:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Enterprise Admin** | `admin@bizpilot.io` | `Admin123!` | Unrestricted full access across all modules |
| **Warehouse Manager**| `manager@bizpilot.io`| `Admin123!` | Inventory, Purchasing, Sales, Warehouses |
| **Warehouse Staff**  | `staff@bizpilot.io`  | `Admin123!` | Adjustments, GRN Receipts, Pick & Pack |
| **Financial Auditor**| `auditor@bizpilot.io`| `Admin123!` | Read-only reports, ledger, and audit logs |

---

## 7. Running Automated Tests

BizPilot features automated test coverage across both backend business invariants and frontend user flows.

### Backend Test Suite (Pytest)

Executes concurrency stress tests, transaction rollbacks, multi-warehouse permissions, PO/SO workflows, and numbering isolation:

```bash
cd backend
pytest -v
```

**Results:**
```
tests/test_auth_rbac.py::test_user_login_success PASSED
tests/test_auth_rbac.py::test_invalid_credentials PASSED
tests/test_auth_rbac.py::test_rbac_permission_denied PASSED
tests/test_master_data.py::test_create_product_success PASSED
tests/test_master_data.py::test_duplicate_sku_rejection PASSED
tests/test_inventory_concurrency.py::test_stock_adjustment_dual_write PASSED
tests/test_inventory_concurrency.py::test_negative_stock_prevention PASSED
tests/test_inventory_concurrency.py::test_inter_warehouse_transfer_atomicity PASSED
tests/test_purchasing_workflow.py::test_full_purchase_order_lifecycle PASSED
tests/test_purchasing_workflow.py::test_cannot_receive_unapproved_po PASSED
tests/test_sales_workflow.py::test_full_sales_order_lifecycle PASSED

======================== 11 passed in 19.48s ========================
```

### Frontend Test Suite (Vitest)

Tests component mounting, authentication state management, and stock mathematical invariant equations:

```bash
cd frontend
npm test
```

**Results:**
```
 ✓ src/tests/components.test.tsx (2 tests)

 Test Files  1 passed (1)
      Tests  2 passed (2)
   Duration  0.88s
```

---

## 8. Database Schema Overview

BizPilot registers 26 relational tables across 10 functional modules:

- **Auth & Access**: `users`, `roles`, `permissions`, `user_roles`, `user_warehouses`
- **Locations**: `locations`, `warehouses`
- **Products**: `product_categories`, `units_of_measure`, `products`
- **Counterparties**: `suppliers`, `customers`
- **Inventory Engine**: `stock_levels`, `stock_movements`, `stock_adjustments`, `stock_transfers`
- **Purchasing**: `purchase_orders`, `purchase_order_items`, `goods_receipt_notes`, `goods_receipt_items`
- **Sales**: `sales_orders`, `sales_order_items`, `shipments`, `shipment_items`
- **Cross-Cutting**: `sequence_generators`, `audit_logs`, `outbox_events`
