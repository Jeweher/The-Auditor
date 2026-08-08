"""
File: app/api/v1/routers/admin.py
Folder: backend/app/api/v1/routers
Purpose: Admin-only endpoints. Every route here is protected by
         require_admin. Scope is intentionally limited to account
         management for now — assessment content stays private, see
         admin_service.py for the rationale.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_user_repository
from app.api.v1.deps_admin import require_admin
from app.application.schemas.admin import (
    AdminUserResponse,
    UpdateUserActiveRequest,
    UpdateUserRoleRequest,
)
from app.application.services.admin_service import AdminService
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepositoryPort

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_admin_service(
    repo: Annotated[UserRepositoryPort, Depends(get_user_repository)],
) -> AdminService:
    return AdminService(repo)


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> list[User]:
    return service.list_users()


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
def update_user_role(
    user_id: UUID,
    payload: UpdateUserRoleRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> User:
    return service.set_user_role(user_id, payload.role)


@router.patch("/users/{user_id}/active", response_model=AdminUserResponse)
def update_user_active(
    user_id: UUID,
    payload: UpdateUserActiveRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> User:
    return service.set_user_active(user_id, payload.is_active)