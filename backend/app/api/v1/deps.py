"""
File: app/api/v1/deps.py
Folder: backend/app/api/v1
Purpose: Reusable FastAPI dependencies for the v1 API - wiring the DB
         session into repositories/services, extracting the current
         authenticated user, and wiring the knowledge base services
         (vector store + embedding provider are process-wide singletons,
         not created per request, since the embedding model is expensive
         to load).
"""
from app.infrastructure.security.encryption_service import EncryptionService
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.domain.ports.user_repository import UserRepositoryPort
from app.application.services.auth_service import AuthService
from app.application.services.assessment_service import AssessmentService
from app.application.services.knowledge_base_ingestion_service import KnowledgeBaseIngestionService
from app.application.services.control_context_builder import ControlContextBuilder
from app.application.services.evidence_services import (
    EvidenceAnalyzerService,
    EvidenceRequirementDetector,
)
from app.application.services.knowledge_base_query_service import KnowledgeBaseQueryService
from app.application.services.llm_services import AnswerClassifierService, QuestionGeneratorService
from app.application.services.maturity_engine import MaturityAssessmentEngine
from app.application.services.recommendation_service import RecommendationService
from app.domain.entities.user import User
from app.domain.ports.embedding_provider import EmbeddingProviderPort
from app.domain.ports.llm_client import LLMPort
from app.domain.ports.file_storage import FileStoragePort
from app.domain.ports.vector_store import VectorStorePort
from app.application.services.email_verification_service import EmailVerificationService
from app.domain.ports.email_sender import EmailSenderPort
from app.infrastructure.db.repositories.email_verification_repository import (
    SqlAlchemyEmailVerificationRepository,
)
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.email.factory import build_email_sender
from app.infrastructure.embeddings.labse_embedding_provider import LaBSEEmbeddingProvider
from app.infrastructure.llm.factory import build_llm_client
from app.infrastructure.storage.factory import build_file_storage
from app.infrastructure.vector_store.chroma_store import ChromaVectorStore

bearer_scheme = HTTPBearer()


def get_user_repository(db: Annotated[Session, Depends(get_db)]) -> UserRepositoryPort:
    return SqlAlchemyUserRepository(db)


def get_auth_service(repository: Annotated[UserRepositoryPort, Depends(get_user_repository)]) -> AuthService:
    return AuthService(repository)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return auth_service.get_current_user(credentials.credentials)
@lru_cache
def _email_sender_singleton() -> EmailSenderPort:
    return build_email_sender()


def get_email_sender() -> EmailSenderPort:
    return _email_sender_singleton()


def get_email_verification_service(
    db: Annotated[Session, Depends(get_db)],
    email_sender: Annotated[EmailSenderPort, Depends(get_email_sender)],
) -> EmailVerificationService:
    user_repository = SqlAlchemyUserRepository(db)
    verification_repository = SqlAlchemyEmailVerificationRepository(db)
    return EmailVerificationService(user_repository, verification_repository, email_sender)


# --- Knowledge base: process-wide singletons ---------------------------
# The embedding model (LaBSE) and the Chroma HTTP client are expensive/
# stateless-safe to reuse across requests, so they're cached rather than
# constructed per request like the DB-backed services above.

@lru_cache
def _vector_store_singleton() -> VectorStorePort:
    return ChromaVectorStore()


@lru_cache
def _embedding_provider_singleton() -> EmbeddingProviderPort:
    return LaBSEEmbeddingProvider()


def get_vector_store() -> VectorStorePort:
    return _vector_store_singleton()


def get_embedding_provider() -> EmbeddingProviderPort:
    return _embedding_provider_singleton()


def get_kb_ingestion_service(
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
    embeddings: Annotated[EmbeddingProviderPort, Depends(get_embedding_provider)],
) -> KnowledgeBaseIngestionService:
    return KnowledgeBaseIngestionService(vector_store, embeddings)


def get_kb_query_service(
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
    embeddings: Annotated[EmbeddingProviderPort, Depends(get_embedding_provider)],
) -> KnowledgeBaseQueryService:
    return KnowledgeBaseQueryService(vector_store, embeddings)

@lru_cache
def _llm_singleton() -> LLMPort:
    return build_llm_client()


def get_llm_client() -> LLMPort:
    return _llm_singleton()


@lru_cache
def _file_storage_singleton() -> FileStoragePort:
    return build_file_storage()
@lru_cache
def _encryption_service_singleton() -> EncryptionService:
    return EncryptionService()


def get_encryption_service() -> EncryptionService:
    return _encryption_service_singleton()

def get_file_storage() -> FileStoragePort:
    return _file_storage_singleton()


def get_assessment_service(
    db: Annotated[Session, Depends(get_db)],
    query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
    llm: Annotated[LLMPort, Depends(get_llm_client)],
    file_storage: Annotated[FileStoragePort, Depends(get_file_storage)],
    encryption_service: Annotated[EncryptionService, Depends(get_encryption_service)],
) -> AssessmentService:
    context_builder = ControlContextBuilder(vector_store)
    return AssessmentService(
        db,
        query_service,
        context_builder=context_builder,
        question_generator=QuestionGeneratorService(llm),
        answer_classifier=AnswerClassifierService(llm),
        evidence_detector=EvidenceRequirementDetector(llm),
        evidence_analyzer=EvidenceAnalyzerService(llm),
        maturity_engine=MaturityAssessmentEngine(llm),
        recommendation_service=RecommendationService(llm),
        file_storage=file_storage,
        encryption_service=encryption_service,
    )