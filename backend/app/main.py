from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.common.schemas import APIResponse, ErrorDetail, ErrorResponse, HealthCheckResponse
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.idempotency import IdempotencyMiddleware
from app.core.logging import logger, setup_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import hash_password
from app.db.session import async_session_factory, engine, init_db
from app.modules.users.models import User

# Import all models to ensure metadata registration
import app.db.models  # noqa: F401

# Import module routers
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.service import AuthService
from app.modules.customers.service import router as customers_router
from app.modules.inventory.router import router as inventory_router
from app.modules.locations.models import Location, Warehouse
from app.modules.locations.router import router as locations_router
from app.modules.products.models import ProductCategory, UnitOfMeasure
from app.modules.products.router import router as products_router
from app.modules.purchasing.router import router as purchasing_router
from app.modules.sales.router import router as sales_router
from app.modules.reporting.router import router as reporting_router
from app.modules.suppliers.service import router as suppliers_router
from app.modules.users.router import router as users_router


async def seed_initial_metadata():
    """Seed foundational master data if database is empty."""
    async with async_session_factory() as session:
        # Seed default Admin and demo accounts
        await AuthService.seed_default_admin(session)

        # Seed additional role demo accounts
        for email, name, role in [
            ("manager@bizpilot.io", "Warehouse Manager", "MANAGER"),
            ("staff@bizpilot.io", "Floor Operator", "STAFF"),
            ("auditor@bizpilot.io", "Compliance Auditor", "AUDITOR"),
        ]:
            u_res = await session.execute(select(User).where(User.email == email))
            if not u_res.scalar_one_or_none():
                session.add(
                    User(
                        email=email,
                        hashed_password=hash_password("Admin123!"),
                        full_name=name,
                        role=role,
                        is_active=True,
                        is_superuser=False,
                    )
                )
        await session.commit()

        # Seed default location and warehouse if empty
        loc_res = await session.execute(select(Location))
        if not loc_res.scalars().first():
            loc1 = Location(
                code="LOC-HQ",
                name="Headquarters Logistics Center",
                address="100 Enterprise Way",
                city="New York",
                country="USA",
            )
            loc2 = Location(
                code="LOC-WEST",
                name="West Coast Distribution Hub",
                address="500 Pacific Boulevard",
                city="Los Angeles",
                country="USA",
            )
            session.add_all([loc1, loc2])
            await session.flush()

            wh1 = Warehouse(location_id=loc1.id, code="WH-NYC-01", name="Main Warehouse NYC")
            wh2 = Warehouse(location_id=loc2.id, code="WH-LAX-01", name="Port Terminal Warehouse LAX")
            session.add_all([wh1, wh2])
            await session.flush()

        # Seed UOMs
        uom_res = await session.execute(select(UnitOfMeasure))
        if not uom_res.scalars().first():
            uoms = [
                UnitOfMeasure(code="PCS", name="Pieces"),
                UnitOfMeasure(code="BOX", name="Boxes"),
                UnitOfMeasure(code="KG", name="Kilograms"),
                UnitOfMeasure(code="PALLET", name="Pallets"),
            ]
            session.add_all(uoms)

        # Seed Categories
        cat_res = await session.execute(select(ProductCategory))
        if not cat_res.scalars().first():
            cats = [
                ProductCategory(code="ELEC", name="Electronics", description="Consumer and enterprise hardware"),
                ProductCategory(code="RAW", name="Raw Materials", description="Industrial inputs and components"),
                ProductCategory(code="PACK", name="Packaging", description="Boxes, crates, and shipping materials"),
            ]
            session.add_all(cats)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing BizPilot enterprise inventory database schema...")
    await init_db()
    await seed_initial_metadata()
    logger.info("BizPilot services initialized successfully.")
    yield
    logger.info("Shutting down BizPilot services...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Cross-cutting middlewares
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                message=exc.message,
                code=exc.__class__.__name__,
                details=exc.details,
            ),
            correlation_id=correlation_id,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                message="Request validation error",
                code="ValidationError",
                details={"errors": exc.errors()},
            ),
            correlation_id=correlation_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.exception(f"Unhandled server error: {str(exc)}", extra={"correlation_id": correlation_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                message="An internal server error occurred.",
                code="InternalServerError",
                details={},
            ),
            correlation_id=correlation_id,
        ).model_dump(),
    )


# Health & Readiness Checks
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_status,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )


# Register all business routers under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(locations_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(customers_router, prefix=settings.API_V1_STR)
app.include_router(suppliers_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(purchasing_router, prefix=settings.API_V1_STR)
app.include_router(sales_router, prefix=settings.API_V1_STR)
app.include_router(reporting_router, prefix=f"{settings.API_V1_STR}/reporting")
app.include_router(reporting_router, prefix=f"{settings.API_V1_STR}/reports")
app.include_router(audit_router, prefix=settings.API_V1_STR)
