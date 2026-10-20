import asyncio
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_bizpilot.db"

from app.core.config import settings
from app.core.permissions import RoleEnum
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.models import Location, Warehouse, User, UserWarehouseAccess, UnitOfMeasure, ProductCategory, Product, Customer, Supplier
from app.db.session import get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test_bizpilot.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    # Locations & Warehouses
    loc = Location(code="LOC-TEST", name="Test Location")
    db_session.add(loc)
    await db_session.flush()

    wh1 = Warehouse(location_id=loc.id, code="WH-01", name="Main Test Warehouse")
    wh2 = Warehouse(location_id=loc.id, code="WH-02", name="Secondary Test Warehouse")
    db_session.add_all([wh1, wh2])
    await db_session.flush()

    # Users
    admin_user = User(
        email="admin@test.io",
        hashed_password=hash_password("Password123!"),
        full_name="Admin Test",
        role=RoleEnum.ADMIN.value,
        is_active=True,
        is_superuser=True,
    )
    wh_mgr = User(
        email="manager@test.io",
        hashed_password=hash_password("Password123!"),
        full_name="Manager Test",
        role=RoleEnum.WAREHOUSE_MANAGER.value,
        is_active=True,
    )
    sales_user = User(
        email="sales@test.io",
        hashed_password=hash_password("Password123!"),
        full_name="Sales Test",
        role=RoleEnum.SALES.value,
        is_active=True,
    )
    purchaser_user = User(
        email="purchaser@test.io",
        hashed_password=hash_password("Password123!"),
        full_name="Purchaser Test",
        role=RoleEnum.PURCHASER.value,
        is_active=True,
    )
    db_session.add_all([admin_user, wh_mgr, sales_user, purchaser_user])
    await db_session.flush()

    # Authorize manager only for WH-01
    db_session.add(UserWarehouseAccess(user_id=wh_mgr.id, warehouse_id=wh1.id))
    db_session.add(UserWarehouseAccess(user_id=sales_user.id, warehouse_id=wh1.id))
    db_session.add(UserWarehouseAccess(user_id=purchaser_user.id, warehouse_id=wh1.id))

    # Master data
    uom = UnitOfMeasure(code="PCS", name="Pieces")
    cat = ProductCategory(code="TESTCAT", name="Test Category")
    db_session.add_all([uom, cat])
    await db_session.flush()

    prod = Product(
        sku="SKU-TEST-001",
        name="Test Widget A",
        uom_id=uom.id,
        category_id=cat.id,
        cost_price=10.00,
        selling_price=15.00,
        tax_rate=5.00,
        reorder_level=5,
    )
    cust = Customer(code="CUST-001", name="Acme Retail", email="acme@test.com")
    supp = Supplier(code="SUPP-001", name="Global Parts Ltd", email="supplier@test.com")
    db_session.add_all([prod, cust, supp])

    await db_session.commit()

    return {
        "location": loc,
        "warehouse1": wh1,
        "warehouse2": wh2,
        "admin": admin_user,
        "manager": wh_mgr,
        "sales": sales_user,
        "purchaser": purchaser_user,
        "product": prod,
        "customer": cust,
        "supplier": supp,
    }


def auth_header(user: User, warehouse_ids: list[int] = None) -> dict:
    wids = warehouse_ids or []
    token = create_access_token(user.id, user.role, wids)
    return {"Authorization": f"Bearer {token}"}
