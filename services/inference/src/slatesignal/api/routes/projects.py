from fastapi import APIRouter, HTTPException, Response, status

from slatesignal.api.dependencies import CurrentUser, DbSession
from slatesignal.domain.schemas import SavedProjectCreate, SavedProjectPublic
from slatesignal.repositories.projects import ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[SavedProjectPublic])
def list_projects(user: CurrentUser, db: DbSession) -> list[SavedProjectPublic]:
    return ProjectRepository(db).list_for_user(user)


@router.post("", response_model=SavedProjectPublic, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: SavedProjectCreate,
    user: CurrentUser,
    db: DbSession,
) -> SavedProjectPublic:
    return ProjectRepository(db).create(user, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: CurrentUser, db: DbSession) -> Response:
    if not ProjectRepository(db).delete(user, project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
