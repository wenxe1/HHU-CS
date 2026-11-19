from beanie import init_beanie

from app.config import MONGODB_URL
from app.models.user import User
from app.models.course import Course
from app.models.knowledge_point import KnowledgePoint
from app.models.knowledge_graph import KnowledgeGraphState
from app.models.question import Question
from app.models.answer_record import AnswerRecord

DOCUMENT_MODELS = [
    User,
    Course,
    KnowledgePoint,
    KnowledgeGraphState,
    Question,
    AnswerRecord,
]


async def init_db():
    await init_beanie(
        connection_string=MONGODB_URL,
        document_models=DOCUMENT_MODELS,
    )
