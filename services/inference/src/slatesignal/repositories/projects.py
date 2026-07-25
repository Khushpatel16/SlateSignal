import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.domain.models import SavedProject, User
from slatesignal.domain.schemas import SavedProjectCreate, SavedProjectPublic


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user: User) -> list[SavedProjectPublic]:
        statement = (
            select(SavedProject)
            .where(SavedProject.user_id == user.id)
            .order_by(SavedProject.updated_at.desc())
        )
        return [self._public(project) for project in self.db.scalars(statement)]

    def create(self, user: User, payload: SavedProjectCreate) -> SavedProjectPublic:
        project = SavedProject(
            user_id=user.id,
            title=payload.title,
            project_type=payload.project_type,
            payload_json=json.dumps(payload.payload, separators=(",", ":"), sort_keys=True),
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return self._public(project)

    def delete(self, user: User, project_id: str) -> bool:
        statement = select(SavedProject).where(
            SavedProject.id == project_id,
            SavedProject.user_id == user.id,
        )
        project = self.db.scalar(statement)
        if not project:
            return False
        self.db.delete(project)
        self.db.commit()
        return True

    @staticmethod
    def _public(project: SavedProject) -> SavedProjectPublic:
        return SavedProjectPublic(
            id=project.id,
            title=project.title,
            project_type=project.project_type,
            payload=json.loads(project.payload_json),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
