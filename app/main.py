
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.investigation import router as investigation_router
from app.config.settings import settings
from app.db.database import engine


app = FastAPI(
    title="Manufacturing Quality Investigation Agent",
    description=(
        "Manufacturing quality investigation platform providing controlled access "
        "to manufacturing data, evidence, traceability, and investigation workflows."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS - allow the local demo UI to call this API
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

app.include_router(investigation_router)


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@app.get("/", tags=["meta"])
def root():
    return {
        "application": settings.app_name,
        "environment": settings.environment,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }

# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


@app.get("/readiness", tags=["system"])
def readiness():
    checks = {
        "database": "not_checked",
    }

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        checks["database"] = "ready"

        return {
            "status": "ready",
            "checks": checks,
        }

    except Exception as exc:

        return {
            "status": "not_ready",
            "checks": checks,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Database information
# ---------------------------------------------------------------------------

@app.get("/database/info", tags=["database"])
def database_info():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        return {
            "status": "connected",
            "database_url": settings.database_url_safe,
            "tables": sorted(tables),
            "table_count": len(tables),
        }

    except Exception as exc:
        return {
            "status": "error",
            "database_url": settings.database_url_safe,
            "error": str(exc),
        }