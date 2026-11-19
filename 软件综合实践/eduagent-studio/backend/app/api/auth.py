from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.api.dependencies import get_auth_service
from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest
from app.schemas.common import ApiResponse, error, success
from app.services.auth_service import (
    AuthService,
    InvalidCredentials,
    PasswordConfirmationMismatch,
    UsernameAlreadyExists,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse)
async def register(
    request: AuthRegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        result = await service.register(request)
    except PasswordConfirmationMismatch:
        return JSONResponse(
            status_code=400,
            content=error(400, "password confirmation does not match"),
        )
    except UsernameAlreadyExists:
        return JSONResponse(
            status_code=409,
            content=error(409, "username already exists"),
        )

    return success(result)


@router.post("/login", response_model=ApiResponse)
async def login(
    request: AuthLoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        result = await service.login(request)
    except InvalidCredentials:
        return JSONResponse(
            status_code=401,
            content=error(401, "invalid username or password"),
        )

    return success(result)
