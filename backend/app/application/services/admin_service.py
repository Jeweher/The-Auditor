"""
File: app/application/services/admin_service.py
Folder: backend/app/application/services
Purpose: Admin-only operations. Every method here assumes the caller has
         already been verified as an admin by the require_admin dependency —
         this service does not re-check permissions, it only implements the
         actions.

         Scope note: this service deliberately exposes ONLY account
         management (list users, toggle active, change role). It never
         exposes another user's assessment content — see the "Monitor
         assessments" module, which is metadata-only by design (privacy by
         design: an admin can see that an assessment exists and its
         progress, never its answers, evidence, or findings).
"""

from uuid import UUID

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.ports.user_repository import UserRepositoryPort

VALID_ROLES = ("user", "admin")


class AdminService:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._repo = user_repository

    def list_users(self):
        return self._repo.list_all()

    def set_user_role(self, user_id: UUID, role: str):
        if role not in VALID_ROLES:
            raise ValidationError(f"role must be one of {VALID_ROLES}.")
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return self._repo.set_role(user_id, role)

    def set_user_active(self, user_id: UUID, is_active: bool):
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return self._repo.set_active(user_id, is_active)