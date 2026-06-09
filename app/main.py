from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError

from app.config.logging_config import configure_logging
from app.config.settings import settings
from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo
from app.middleware.exception_handlers import register_exception_handlers
from app.routes.admin.auth import router as admin_auth_pages_router
from app.routes.api.admin_auth import router as admin_auth_router
from app.routes.api.articles import router as articles_router
from app.routes.api.categories import router as categories_router
from app.routes.api.health import router as health_router
from app.routes.api.newsletter import router as newsletter_router
from app.routes.api.search import router as search_router
from app.routes.api.submissions import router as submissions_router
from app.routes.api.tags import router as tags_router
from app.routes.public.articles import router as public_articles_router
from app.routes.public.categories import router as public_categories_router
from app.routes.public.home import router as home_router
from app.routes.public.search import router as public_search_router


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    try:
        await connect_to_mongo()
        await create_indexes()
        app.state.mongodb_available = True
        logger.info("MongoDB connection established")
    except PyMongoError as exc:
        app.state.mongodb_available = False
        await close_mongo_connection()
        if settings.mongodb_required:
            logger.exception("MongoDB is required but unavailable")
            raise
        logger.warning("MongoDB unavailable; continuing without database: %s", exc)

    yield
    logger.info("Shutting down %s", settings.app_name)
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

register_exception_handlers(app)
app.include_router(admin_auth_router)
app.include_router(articles_router)
app.include_router(categories_router)
app.include_router(health_router)
app.include_router(newsletter_router)
app.include_router(search_router)
app.include_router(submissions_router)
app.include_router(tags_router)
app.include_router(public_articles_router)
app.include_router(public_categories_router)
app.include_router(home_router)
app.include_router(public_search_router)
app.include_router(admin_auth_pages_router)
