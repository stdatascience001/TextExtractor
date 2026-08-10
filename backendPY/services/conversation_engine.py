import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update

from models.models import Conversation, Message, ActivityEvent

logger = logging.getLogger("conversation_engine")

class ConversationContext(BaseModel):
    conversation_id: str
    summary: Optional[str] = None
    recent_messages: List[Dict[str, Any]] = Field(default_factory=list)
    selected_documents: List[str] = Field(default_factory=list)
    token_budget: int
    statistics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ----------------- Specialized Conversation Components -----------------

class ConversationRepository:
    async def create(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        selected_document_ids: Optional[List[str]] = None,
        document_id: Optional[uuid.UUID] = None
    ) -> Conversation:
        conv = Conversation(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=user_id,
            document_id=document_id,
            title=title,
            selected_document_ids=selected_document_ids or [],
            status="ACTIVE",
            summary_metadata={}
        )
        db.add(conv)
        await db.flush()
        return conv

    async def get(self, db: AsyncSession, conversation_id: uuid.UUID) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        include_archived: bool = False
    ) -> List[Conversation]:
        allowed_statuses = ["ACTIVE"]
        if include_archived:
            allowed_statuses.append("ARCHIVED")
            
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.document_id == document_id,
                    Conversation.user_id == user_id,
                    Conversation.status.in_(allowed_statuses)
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        include_archived: bool = False
    ) -> List[Conversation]:
        allowed_statuses = ["ACTIVE"]
        if include_archived:
            allowed_statuses.append("ARCHIVED")
            
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.project_id == project_id,
                    Conversation.user_id == user_id,
                    Conversation.status.in_(allowed_statuses)
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        title: Optional[str] = None,
        selected_document_ids: Optional[List[str]] = None
    ) -> Optional[Conversation]:
        conv = await self.get(db, conversation_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if selected_document_ids is not None:
            conv.selected_document_ids = selected_document_ids
        conv.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return conv

    async def update_status(self, db: AsyncSession, conversation_id: uuid.UUID, status: str) -> bool:
        conv = await self.get(db, conversation_id)
        if not conv:
            return False
        conv.status = status
        conv.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return True

class HistoryManager:
    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        retrieval_reference: Optional[str] = None,
        status: str = "COMPLETED"
    ) -> Message:
        # Calculate simple token count based on word count estimation
        words = content.split()
        estimated_tokens = int(len(words) * 1.3)
        
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token_count": estimated_tokens,
            "attachments": attachments or [],
            "provider": provider,
            "model": model,
            "retrieval_reference": retrieval_reference,
            "status": status
        }
        
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
            message_metadata=meta
        )
        db.add(msg)
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return msg

    async def fetch_history(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

class BaseCompressionStrategy(ABC):
    @abstractmethod
    def compress(self, messages: List[Message]) -> str:
        pass

class KeywordCompression(BaseCompressionStrategy):
    def compress(self, messages: List[Message]) -> str:
        summary_turns = []
        for m in messages:
            words = (m.content or "").split()
            snippet = " ".join(words[:6]) + "..." if len(words) > 6 else m.content
            summary_turns.append(f"{m.role.capitalize()}: {snippet}")
        return "Dialog History Summary: " + "; ".join(summary_turns)

class SemanticCompression(BaseCompressionStrategy):
    def compress(self, messages: List[Message]) -> str:
        # Fallback keyword compression
        return KeywordCompression().compress(messages)

class LLMCompression(BaseCompressionStrategy):
    def compress(self, messages: List[Message]) -> str:
        # Fallback keyword compression
        return KeywordCompression().compress(messages)

class MemoryManager:
    def __init__(self, strategy: Optional[BaseCompressionStrategy] = None):
        self.strategy = strategy or KeywordCompression()

    async def compress_history(
        self,
        db: AsyncSession,
        conversation: Conversation,
        messages: List[Message],
        word_limit: int = 1500
    ) -> Optional[str]:
        total_words = sum(len((m.content or "").split()) for m in messages)
        if total_words <= word_limit:
            return None

        earlier_messages = messages[:-4] if len(messages) > 4 else []
        if not earlier_messages:
            return None

        summary_text = self.strategy.compress(earlier_messages)
        
        # Maintain summary metadata details
        meta = {
            "summary_version": "1.0.0",
            "summary_algorithm": self.strategy.__class__.__name__,
            "summary_updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        conversation.summary = summary_text
        conversation.summary_metadata = meta
        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return summary_text

class TokenBudgetManager:
    def calculate_tokens(self, messages: List[Message], summary: Optional[str] = None) -> Dict[str, int]:
        message_tokens = 0
        for m in messages:
            meta = m.message_metadata or {}
            tokens = meta.get("token_count")
            if tokens is None:
                tokens = int(len((m.content or "").split()) * 1.3)
            message_tokens += tokens
            
        summary_tokens = int(len((summary or "").split()) * 1.3)
        return {
            "message_tokens": message_tokens,
            "summary_tokens": summary_tokens,
            "total_tokens": message_tokens + summary_tokens
        }

class ConversationContextBuilder:
    async def build(
        self,
        conversation: Conversation,
        messages: List[Message],
        token_usage: Dict[str, int],
        budget_limit: int = 4000
    ) -> ConversationContext:
        recent_msg_payloads = []
        for m in messages[-4:]: # Keep last 4 turns as active memory context
            recent_msg_payloads.append({
                "role": m.role,
                "content": m.content,
                "metadata": m.message_metadata or {}
            })
            
        return ConversationContext(
            conversation_id=str(conversation.id),
            summary=conversation.summary,
            recent_messages=recent_msg_payloads,
            selected_documents=conversation.selected_document_ids or [],
            token_budget=max(0, budget_limit - token_usage["total_tokens"]),
            statistics={
                "total_messages": len(messages),
                "token_usage": token_usage
            },
            metadata=conversation.summary_metadata or {}
        )

# ----------------- Central Engine Orchestrator -----------------

class ConversationEngine:
    def __init__(
        self,
        repository: Optional[ConversationRepository] = None,
        history_manager: Optional[HistoryManager] = None,
        memory_manager: Optional[MemoryManager] = None,
        token_budget_manager: Optional[TokenBudgetManager] = None,
        context_builder: Optional[ConversationContextBuilder] = None
    ):
        self.repository = repository or ConversationRepository()
        self.history_manager = history_manager or HistoryManager()
        self.memory_manager = memory_manager or MemoryManager()
        self.token_budget_manager = token_budget_manager or TokenBudgetManager()
        self.context_builder = context_builder or ConversationContextBuilder()

    # Backwards compatible classmethod wrappers

    @classmethod
    async def create_conversation(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        selected_document_ids: Optional[List[str]] = None,
        document_id: Optional[uuid.UUID] = None
    ) -> Conversation:
        instance = cls()
        conv = await instance.repository.create(db, project_id, user_id, title, selected_document_ids, document_id)
        db.add(ActivityEvent(
            user_id=user_id,
            project_id=project_id,
            action_name="CONVERSATION_CREATED",
            payload={"conversation_id": str(conv.id), "title": title}
        ))
        await db.commit()
        return conv

    @classmethod
    async def get_conversation(cls, db: AsyncSession, conversation_id: uuid.UUID) -> Optional[Conversation]:
        instance = cls()
        return await instance.repository.get(db, conversation_id)

    @classmethod
    async def list_conversations(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        include_archived: bool = False
    ) -> List[Conversation]:
        instance = cls()
        # Ensure compatibility mapping
        archived_param = include_archived
        return await instance.repository.list_by_project(db, project_id, user_id, include_archived=archived_param)

    @classmethod
    async def list_conversations_by_document(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        include_archived: bool = False
    ) -> List[Conversation]:
        instance = cls()
        return await instance.repository.list_by_document(db, document_id, user_id, include_archived=include_archived)

    @classmethod
    async def update_conversation(
        cls,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        title: Optional[str] = None,
        selected_document_ids: Optional[List[str]] = None
    ) -> Optional[Conversation]:
        instance = cls()
        return await instance.repository.update(db, conversation_id, title, selected_document_ids)

    @classmethod
    async def archive_conversation(cls, db: AsyncSession, conversation_id: uuid.UUID) -> bool:
        instance = cls()
        return await instance.repository.update_status(db, conversation_id, "ARCHIVED")

    @classmethod
    async def delete_conversation(cls, db: AsyncSession, conversation_id: uuid.UUID) -> bool:
        instance = cls()
        return await instance.repository.update_status(db, conversation_id, "DELETED")

    @classmethod
    async def restore_conversation(cls, db: AsyncSession, conversation_id: uuid.UUID) -> bool:
        instance = cls()
        return await instance.repository.update_status(db, conversation_id, "ACTIVE")

    @classmethod
    async def add_message(
        cls,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        instance = cls()
        return await instance.history_manager.add_message(db, conversation_id, role, content, citations)

    @classmethod
    async def get_message_history(
        cls,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 20
    ) -> List[Message]:
        instance = cls()
        return await instance.history_manager.fetch_history(db, conversation_id, limit)

    @classmethod
    async def compress_history(
        cls,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        word_limit: int = 1500
    ) -> Optional[str]:
        instance = cls()
        conv = await instance.repository.get(db, conversation_id)
        if not conv:
            return None
        messages = await instance.history_manager.fetch_history(db, conversation_id, limit=200)
        return await instance.memory_manager.compress_history(db, conv, messages, word_limit)

    # Modular invocation API for advanced orchestration context building
    async def build_context(self, db: AsyncSession, conversation_id: uuid.UUID, budget_limit: int = 4000) -> Optional[ConversationContext]:
        conv = await self.repository.get(db, conversation_id)
        if not conv:
            return None
        messages = await self.history_manager.fetch_history(db, conversation_id, limit=200)
        token_usage = self.token_budget_manager.calculate_tokens(messages, conv.summary)
        return await self.context_builder.build(conv, messages, token_usage, budget_limit)

