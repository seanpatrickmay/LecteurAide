from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api import books, progress, admin


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LingoLens Reader")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(books.router)
    app.include_router(progress.router)
    app.include_router(admin.router, prefix="/admin")
    return app


app = create_app()
