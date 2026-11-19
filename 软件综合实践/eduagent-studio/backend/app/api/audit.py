from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.api.dependencies import get_audit_service
from app.schemas.audit import AuditResourceRequest
from app.schemas.common import ApiResponse, error, success
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/resource/{resource_id}", response_model=ApiResponse)
async def audit_resource(
    resource_id: str,
    request: AuditResourceRequest,
    service: Annotated[AuditService, Depends(get_audit_service)],
):
    result = await service.audit_resource(resource_id, request)
    if result is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "resource not found"),
        )
    return success(result)
