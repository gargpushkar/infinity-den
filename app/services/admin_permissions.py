from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException
from fastapi import status as http_status

from app.models.admin import AdminRole
from app.schemas.admin import AdminRead
from app.services.admin_session import get_current_admin


ADMIN_ROLE: AdminRole = "admin"
EDITOR_ROLE: AdminRole = "editor"

ARTICLE_WRITE_ROLES: tuple[AdminRole, ...] = (ADMIN_ROLE, EDITOR_ROLE)
CONTENT_STRUCTURE_ROLES: tuple[AdminRole, ...] = (ADMIN_ROLE,)
DESTRUCTIVE_ROLES: tuple[AdminRole, ...] = (ADMIN_ROLE,)
SUBMISSION_REVIEW_ROLES: tuple[AdminRole, ...] = (ADMIN_ROLE, EDITOR_ROLE)
ADMIN_USER_MANAGEMENT_ROLES: tuple[AdminRole, ...] = (ADMIN_ROLE,)


def require_admin_roles(
    *allowed_roles: AdminRole,
) -> Callable[..., Awaitable[AdminRead]]:
    async def dependency(
        admin: AdminRead = Depends(get_current_admin),
    ) -> AdminRead:
        if admin.role not in allowed_roles:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Admin role is not allowed to perform this action.",
            )

        return admin

    return dependency


require_article_writer = require_admin_roles(*ARTICLE_WRITE_ROLES)
require_content_manager = require_admin_roles(*CONTENT_STRUCTURE_ROLES)
require_destructive_admin = require_admin_roles(*DESTRUCTIVE_ROLES)
require_submission_reviewer = require_admin_roles(*SUBMISSION_REVIEW_ROLES)
require_admin_manager = require_admin_roles(*ADMIN_USER_MANAGEMENT_ROLES)
