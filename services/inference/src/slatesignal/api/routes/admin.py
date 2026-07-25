from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from slatesignal.api.dependencies import AdminUser, DbSession
from slatesignal.domain.models import AuthSession, SavedProject, User
from slatesignal.domain.schemas import AdminOverview, AdminRecentProject

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverview)
def overview(_: AdminUser, db: DbSession) -> AdminOverview:
    type_counts: dict[str, int] = {}
    type_rows = db.execute(
        select(SavedProject.project_type, func.count()).group_by(SavedProject.project_type)
    ).all()
    for row in type_rows:
        type_counts[row[0]] = int(row[1])
    recent_rows = db.execute(
        select(SavedProject, User.display_name)
        .join(User, SavedProject.user_id == User.id)
        .order_by(SavedProject.updated_at.desc())
        .limit(8)
    ).all()

    return AdminOverview(
        users=db.scalar(select(func.count()).select_from(User)) or 0,
        saved_projects=db.scalar(select(func.count()).select_from(SavedProject)) or 0,
        active_sessions=(
            db.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.expires_at > datetime.now(UTC))
            )
            or 0
        ),
        forecast_projects=type_counts.get("forecast", 0),
        optimization_projects=type_counts.get("optimization", 0),
        recent_projects=[
            AdminRecentProject(
                id=project.id,
                title=project.title,
                project_type=project.project_type,
                owner_name=owner_name,
                updated_at=project.updated_at,
            )
            for project, owner_name in recent_rows
        ],
    )
