from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
import logging
from models import ResponseSignal
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from .schemes.nlp import PushRequest, SearchRequest

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1_nlp"],
)

def get_nlp_controller(request: Request):
    return NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    nlp_controller = get_nlp_controller(request)

    if push_request.do_reset == 1:
        await run_in_threadpool(nlp_controller.reset_vector_db_collection, project)

    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0

    while has_records:
        page_chunks = await chunk_model.get_project_chunks(project_id=project.id, page_no=page_no)
        if not page_chunks:
            break
        page_no += 1

        chunks_ids = list(range(idx, idx + len(page_chunks)))
        idx += len(page_chunks)

        try:
            is_inserted = await run_in_threadpool(
                nlp_controller.index_into_vector_db, project, page_chunks, chunks_ids
            )
        except Exception as e:
            logger.error(f"Error while indexing chunks: {e}")
            is_inserted = False

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value}
            )

        inserted_items_count += len(page_chunks)

    return JSONResponse(
        content={
            "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        }
    )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    collection_info = await run_in_threadpool(get_nlp_controller(request).get_vector_db_collection_info, project)

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info,
        }
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: str, search_request: SearchRequest):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    try:
        results = await run_in_threadpool(
            get_nlp_controller(request).search_vector_db_collection,
            project, search_request.text, search_request.limit,
        )
    except Exception as e:
        logger.error(f"Error while searching: {e}")
        results = None

    if not results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value}
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [result.model_dump() for result in results],
        }
    )

@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: str, search_request: SearchRequest):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    try:
        answer, full_prompt, chat_history, documents = await run_in_threadpool(
            get_nlp_controller(request).answer_rag_question,
            project, search_request.text, search_request.limit,
        )
    except Exception as e:
        logger.error(f"Error while answering: {e}")
        answer, full_prompt, chat_history, documents = None, None, None, None

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.RAG_ANSWER_ERROR.value}
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
            "documents": [doc.model_dump() for doc in documents],
        }
    )
