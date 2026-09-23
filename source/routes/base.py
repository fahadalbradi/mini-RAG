from fastapi import APIRouter, Depends, Request
from helpers.config import get_settings, Settings
from models import ResponseSignal
from models.ProjectModel import ProjectModel

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

@base_router.get("/")
async def welcome(request: Request, app_settings: Settings = Depends(get_settings)):

    return {
        "app_name": app_settings.APP_NAME,
        "app_version": app_settings.APP_VERSION,
        "generation_backend": request.app.generation_backend,
        "embedding_backend": request.app.embedding_backend,
        "generation_model": request.app.generation_client.generation_model_id,
        "embedding_model": request.app.embedding_client.embedding_model_id,
        "vector_db": app_settings.VECTOR_DB_BACKEND,
        "database": request.app.database_backend,
        "warnings": request.app.startup_warnings,
    }

@base_router.get("/projects")
async def list_projects(request: Request, page: int = 1, page_size: int = 50):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    projects, total_pages = await project_model.get_all_projects(page=page, page_size=page_size)

    return {
        "signal": ResponseSignal.PROJECT_LIST_SUCCESS.value,
        "total_pages": total_pages,
        "projects": [project.project_id for project in projects],
    }
