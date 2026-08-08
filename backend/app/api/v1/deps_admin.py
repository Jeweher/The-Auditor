"""
File: app/api/v1/deps_admin.py
Folder: backend/app/api/v1
Purpose: Admin-only route guard. Reuses the existing get_current_user
         dependency, then checks role — a single, reusable gate for every
         endpoint under /api/v1/admin/*.
"""

from typing import Annotated

from fastapi import Depends

from app.api.v1.deps import get_current_user
from app.core.exceptions import ForbiddenError
from app.domain.entities.user import User


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise ForbiddenError("Admin access required.")
    return current_user