import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import OutboxMessage

class OutboxService:
    @staticmethod
    async def publish_fact_created(db: AsyncSession, fact_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Saves a FactCreated domain event inside the outbox message registry within the active transaction boundary."""
        message = OutboxMessage(
            event_type="FactCreated",
            payload={
                "fact_id": str(fact_id),
                "project_id": str(project_id),
                "user_id": str(user_id)
            },
            status="pending"
        )
        db.add(message)
        await db.flush()
