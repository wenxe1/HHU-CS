from app.db.mongodb import get_mongo_database
from app.db.repositories import MongoResourceTaskRepository, ResourceTaskRepository
from app.services.ai_client import AIClient, OpenAICompatibleAIClient
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService, MongoAuthRepository
from app.services.classroom_service import ClassroomService
from app.services.notebook_service import MongoNotebookRepository, NotebookService
from app.services.code_review_service import CodeReviewService
from app.services.rag_service import RAGService
from app.services.resource_service import ResourceGenerateService
from app.services.task_service import TaskService
from app.services.tutor_service import TutorService


def get_resource_task_repository() -> ResourceTaskRepository:
    return MongoResourceTaskRepository(get_mongo_database())


def get_ai_client() -> AIClient:
    return OpenAICompatibleAIClient()


def get_deepseek_ai_client() -> AIClient:
    return get_ai_client()


def get_auth_service() -> AuthService:
    return AuthService(MongoAuthRepository(get_mongo_database()))


def get_notebook_service() -> NotebookService:
    database = get_mongo_database()
    return NotebookService(MongoNotebookRepository(database), get_ai_client())


def get_resource_generate_service() -> ResourceGenerateService:
    return ResourceGenerateService(get_resource_task_repository(), get_ai_client())


def get_task_service() -> TaskService:
    return TaskService(get_resource_task_repository())


def get_tutor_service() -> TutorService:
    return TutorService(get_resource_task_repository(), get_ai_client())


def get_deepseek_tutor_service() -> TutorService:
    return get_tutor_service()


def get_code_review_service() -> CodeReviewService:
    return CodeReviewService(get_resource_task_repository(), get_ai_client())


def get_rag_service() -> RAGService:
    return RAGService(get_resource_task_repository(), get_ai_client())


def get_audit_service() -> AuditService:
    return AuditService(get_resource_task_repository(), get_ai_client())


def get_classroom_service() -> ClassroomService:
    return ClassroomService(get_resource_task_repository(), get_ai_client())
