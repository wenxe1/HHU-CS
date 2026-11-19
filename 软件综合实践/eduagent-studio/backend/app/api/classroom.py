import json
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse, StreamingResponse

from app.api.dependencies import (
    get_classroom_service,
    get_deepseek_tutor_service,
    get_tutor_service,
)
from app.schemas.classroom import (
    ClassroomFlashcardsGenerateRequest,
    ClassroomGenerateRequest,
    ClassroomQuizGenerateRequest,
    FlashcardPracticeRecordRequest,
    FlashcardPracticeResetRequest,
    QuizPracticeRecordRequest,
    UserProfileGenerateRequest,
)
from app.schemas.common import ApiResponse, error, success
from app.schemas.tutor import TutorAskRequest
from app.services.classroom_service import ClassroomService
from app.services.tutor_service import TutorService


router = APIRouter(prefix="/classroom", tags=["classroom"])


@router.get("/studio", response_model=ApiResponse)
async def list_studio_artifacts(
    user_id: str,
    course_id: str,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
    notebook_id: str | None = None,
):
    result = await service.list_studio_artifacts(
        user_id=user_id,
        course_id=course_id,
        notebook_id=notebook_id,
    )
    return success(result)


@router.get("/profile", response_model=ApiResponse)
async def get_user_profile(
    user_id: str,
    course_id: str,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
    notebook_id: str | None = None,
):
    result = await service.get_user_profile(
        user_id=user_id,
        course_id=course_id,
        notebook_id=notebook_id,
    )
    return success(result)


@router.post("/profile/generate", response_model=ApiResponse)
async def regenerate_user_profile(
    request: UserProfileGenerateRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await service.generate_user_profile(
        user_id=request.user_id,
        course_id=request.course_id,
        notebook_id=request.notebook_id,
        force_refresh=request.force_refresh,
    )
    return success(result)


@router.post("/ask", response_model=ApiResponse)
async def ask_in_classroom(
    request: TutorAskRequest,
    service: Annotated[TutorService, Depends(get_deepseek_tutor_service)],
):
    result = await service.ask(request)
    return success(result)


@router.post("/ask/stream")
async def stream_classroom_answer(
    request: TutorAskRequest,
    service: Annotated[TutorService, Depends(get_deepseek_tutor_service)],
):
    async def event_stream():
        try:
            async for event in service.stream_ask(request):
                yield f"{json.dumps(event, ensure_ascii=False)}\n"
        except Exception as exc:
            yield f"{json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/history", response_model=ApiResponse)
async def delete_classroom_chat_history(
    user_id: str,
    service: Annotated[TutorService, Depends(get_tutor_service)],
    course_id: str | None = None,
    notebook_id: str | None = None,
    visit_id: str | None = None,
):
    result = await service.delete_history(
        user_id=user_id,
        course_id=course_id,
        notebook_id=notebook_id,
        visit_id=visit_id,
    )
    return success(result)


@router.post("/generate", response_model=ApiResponse)
async def generate_classroom(
    request: ClassroomGenerateRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await service.generate(request)
    return success(result)


@router.post("/quiz/generate", response_model=ApiResponse)
async def generate_quiz(
    request: ClassroomQuizGenerateRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.generate_quiz(request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.post("/flashcards/generate", response_model=ApiResponse)
async def generate_flashcards(
    request: ClassroomFlashcardsGenerateRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.generate_flashcards(request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.post("/quiz/practice", response_model=ApiResponse)
async def record_quiz_practice(
    request: QuizPracticeRecordRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.record_quiz_practice(request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.post("/flashcards/practice", response_model=ApiResponse)
async def record_flashcard_practice(
    request: FlashcardPracticeRecordRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.record_flashcard_practice(request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.post("/flashcards/{flashcard_set_id}/practice/reset", response_model=ApiResponse)
async def reset_flashcard_practice(
    flashcard_set_id: str,
    request: FlashcardPracticeResetRequest,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.reset_flashcard_practice(
            flashcard_set_id=flashcard_set_id,
            user_id=request.user_id,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.delete("/quiz/{quiz_id}", response_model=ApiResponse)
async def delete_quiz(
    quiz_id: str,
    user_id: str,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.delete_quiz(quiz_id=quiz_id, user_id=user_id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content=error(404, str(exc)))
    return success(result)


@router.delete("/flashcards/{flashcard_set_id}", response_model=ApiResponse)
async def delete_flashcard_set(
    flashcard_set_id: str,
    user_id: str,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    try:
        result = await service.delete_flashcard_set(
            flashcard_set_id=flashcard_set_id,
            user_id=user_id,
        )
    except ValueError as exc:
        return JSONResponse(status_code=404, content=error(404, str(exc)))
    return success(result)


@router.get("/{session_id}", response_model=ApiResponse)
async def get_classroom(
    session_id: str,
    service: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await service.get_classroom(session_id)
    if result is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "classroom not found"),
        )
    return success(result)
