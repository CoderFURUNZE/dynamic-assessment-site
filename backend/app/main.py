from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import admin, auth, content, enrollment, eval, extensions, graph, interview, notes, portrait_dimensions, practice, reco, stages
from app.core.config import settings
from app.core.logging import init_logging
from app.db.bootstrap import bootstrap_defaults
from app.db.session import init_db


def create_app() -> FastAPI:
    init_logging()
    app = FastAPI(title=settings.app_name)

    init_db()
    bootstrap_defaults()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    media_dir = Path(settings.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url, StaticFiles(directory=str(media_dir)), name="media")

    @app.get("/health")
    def health():
        return {"ok": True}

    api = FastAPI(title=settings.app_name)
    api.include_router(auth.router)
    api.include_router(graph.router)
    api.include_router(enrollment.router)
    api.include_router(content.router)
    api.include_router(practice.router)
    api.include_router(eval.router)
    api.include_router(reco.router)
    api.include_router(notes.router)
    api.include_router(extensions.router)
    api.include_router(stages.router)
    api.include_router(portrait_dimensions.router)
    api.include_router(admin.router)
    api.include_router(interview.router)
    app.mount(settings.api_prefix, api)
    return app


app = create_app()
