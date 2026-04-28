from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine
from .utils import setup_logging
from .api import categories, literatures, search, agent, config


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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

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
