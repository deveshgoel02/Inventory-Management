import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import allotments, analytics, audit, auth, catalog, deadlines, imports, inventory, purchasing, reports, sales, settings, users, warehouses
from app.bootstrap import run_bootstrap
from app.core.config import settings as app_settings
from app.core.database import SessionLocal

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("shoexpress")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        run_bootstrap(db)
    finally:
        db.close()
    yield


app = FastAPI(title=app_settings.APP_NAME, version="0.1.0", lifespan=lifespan)

# The Android app (built with Capacitor) always serves its bundled web assets
# from these two fixed origins, regardless of which deployment it's built
# against - so they're safe to always allow, not just something toggled via
# the CORS_ORIGINS env var used for the actual web frontend deployments.
NATIVE_APP_ORIGINS = ["https://localhost", "capacitor://localhost"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*app_settings.CORS_ORIGINS, *NATIVE_APP_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces to the client — log full details server-side,
    # return a generic, safe message to the caller.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred. Please try again or contact support."})


@app.exception_handler(HTTPException)
async def http_exception_logging_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("HTTP %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return await http_exception_handler(request, exc)


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(allotments.router)
app.include_router(purchasing.router)
app.include_router(deadlines.router)
app.include_router(analytics.router)
app.include_router(imports.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(users.router)
app.include_router(audit.router)

# Public static downloads (e.g. the Android APK) - no auth required, since
# these are meant to be shared as plain links, not accessed through the app.
app.mount("/downloads", StaticFiles(directory=STATIC_DIR / "downloads"), name="downloads")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": app_settings.APP_NAME, "environment": app_settings.ENVIRONMENT}
