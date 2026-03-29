# """
# app/main.py
# FastAPI application entry point.
# Serves the HTML frontend at / and the API at /api/v1.
# No Streamlit — the UI is a single self-contained index.html.
# """

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse
# from contextlib import asynccontextmanager
# from pathlib import Path

# from app.routes.api_routes import router
# from app.config.settings import get_settings
# from app.utils.logger import get_logger

# logger   = get_logger("main")
# settings = get_settings()

# # Path to the static frontend folder (frontend/static/)
# STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger.info("=" * 60)
#     logger.info(f"  {settings.app_name} starting up")
#     logger.info(f"  Environment : {settings.app_env}")
#     logger.info(f"  Host        : {settings.app_host}:{settings.app_port}")
#     logger.info(f"  Risk threshold : {settings.risk_threshold}")
#     logger.info(f"  UI  →  http://localhost:{settings.app_port}/")
#     logger.info(f"  API →  http://localhost:{settings.app_port}/docs")
#     logger.info("=" * 60)
#     yield
#     logger.info("Application shutting down.")


# app = FastAPI(
#     title="Supply Chain AI Risk & Decision System",
#     description=(
#         "Multi-agent autonomous system for real-time shipment risk assessment, "
#         "route optimisation, compliance validation, and decision explanation."
#     ),
#     version="1.0.0",
#     lifespan=lifespan,
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# # ── CORS ──────────────────────────────────────────────────────────────────────
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ── API routes (/api/v1/*) ────────────────────────────────────────────────────
# app.include_router(router, prefix="/api/v1")

# # ── Static assets (CSS, JS, images if any) ───────────────────────────────────
# if STATIC_DIR.exists():
#     app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# # ── Root → serve HTML dashboard ──────────────────────────────────────────────
# @app.get("/", include_in_schema=False)
# async def serve_ui():
#     """Serve the SupplyMind AI HTML dashboard."""
#     index = STATIC_DIR / "index.html"
#     if index.exists():
#         return FileResponse(str(index))
#     return {
#         "service": settings.app_name,
#         "error":   "frontend/static/index.html not found",
#         "api_docs": "/docs",
#         "health":   "/api/v1/health",
#     }


# # ── Dev server ────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "app.main:app",
#         host=settings.app_host,
#         port=settings.app_port,
#         reload=settings.debug,
#         log_level="info",
#     )



"""
app/main.py
FastAPI application entry point.
Serves the HTML frontend at / and the API at /api/v1.
No Streamlit — the UI is a single self-contained index.html.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.routes.api_routes import router
from app.routes.fleet_routes import router as fleet_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.export_routes import router as export_router
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger   = get_logger("main")
settings = get_settings()

# Path to the static frontend folder (frontend/static/)
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} starting up")
    logger.info(f"  Environment : {settings.app_env}")
    logger.info(f"  Host        : {settings.app_host}:{settings.app_port}")
    logger.info(f"  Risk threshold : {settings.risk_threshold}")
    logger.info(f"  UI  →  http://localhost:{settings.app_port}/")
    logger.info(f"  API →  http://localhost:{settings.app_port}/docs")
    logger.info("=" * 60)
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title="Supply Chain AI Risk & Decision System",
    description=(
        "Multi-agent autonomous system for real-time shipment risk assessment, "
        "route optimisation, compliance validation, and decision explanation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes (/api/v1/*) ────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")
app.include_router(fleet_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")

# ── Static assets (CSS, JS, images if any) ───────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Root → serve HTML dashboard ──────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the SupplyMind AI HTML dashboard."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {
        "service": settings.app_name,
        "error":   "frontend/static/index.html not found",
        "api_docs": "/docs",
        "health":   "/api/v1/health",
    }


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info",
    )