import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, SessionLocal, engine
from .services.fts_manager import rebuild_fts
from .utils import setup_logging
from .api import categories, literatures, search, agent, config

logger = logging.getLogger(__name__)


def _error_payload(code: str, message: str, errors: list | None = None) -> dict:
    payload = {"error": {"code": code, "message": message}, "detail": message}
    if errors:
        payload["errors"] = errors
    return payload


def _code_for_status(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_409_CONFLICT: "conflict",
    }
    return mapping.get(status_code, "http_error")


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(title="Literature Manager")

    allow_origins = settings.cors_origins if settings.cors_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            rebuild_fts(db)
            db.commit()
        except Exception:
            logger.exception("Failed to rebuild FTS index")
            db.rollback()
        finally:
            db.close()

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "Internal server error"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                _code_for_status(exc.status_code),
                str(exc.detail),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                "validation_error", "Validation error", exc.errors()
            ),
        )

    app.include_router(categories.router, prefix="/categories", tags=["categories"])
    app.include_router(literatures.router, prefix="/literatures", tags=["literatures"])
    app.include_router(search.router, prefix="/search", tags=["search"])
    app.include_router(agent.router, prefix="/agent", tags=["agent"])
    app.include_router(config.router, prefix="/config", tags=["config"])

    @app.get("/")
    def root() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
