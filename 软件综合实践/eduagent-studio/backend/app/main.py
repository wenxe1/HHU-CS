from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.classroom import router as classroom_router
from app.api.notebook import router as notebook_router
from app.api.rag import router as rag_router
from app.api.resource import router as resource_router
from app.api.task import router as task_router
from app.api.tutor import router as tutor_router
from app.database import init_db
from app.db.mongodb import close_mongo_client
from app.routers import course
from app.schemas.common import error
from app.services.ai_client import AIConfigurationError, AIServiceError


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_mongo_client()


app = FastAPI(title="EduAgent Studio API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(classroom_router, prefix="/api")
app.include_router(notebook_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(resource_router, prefix="/api")
app.include_router(task_router, prefix="/api")
app.include_router(tutor_router, prefix="/api")
app.include_router(course.router, prefix="/api")


@app.exception_handler(AIConfigurationError)
async def handle_ai_configuration_error(
    request: Request,
    exc: AIConfigurationError,
):
    return JSONResponse(status_code=503, content=error(503, str(exc)))


@app.exception_handler(AIServiceError)
async def handle_ai_service_error(request: Request, exc: AIServiceError):
    return JSONResponse(status_code=502, content=error(502, str(exc)))


@app.get("/")
def root():
    return {
        "code": 0,
        "message": "EduAgent Studio backend is running",
        "data": {},
    }
