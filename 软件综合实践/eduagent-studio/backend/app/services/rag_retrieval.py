from typing import Any

from app.db.repositories import ResourceTaskRepository
from app.models.rag import RAGDocument
from app.services.ai_client import AIClient


async def resolve_rag_documents(
    repository: ResourceTaskRepository,
    course_id: str,
    user_id: str | None = None,
    notebook_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[RAGDocument]:
    documents = await repository.list_rag_documents(
        user_id=user_id,
        course_id=course_id,
        notebook_id=notebook_id,
    )
    if document_ids:
        selected_ids = set(document_ids)
        documents = [
            document
            for document in documents
            if document.document_id in selected_ids or document.source_id in selected_ids
        ]
    return [
        document
        for document in documents
        if document.upload_status == "success"
    ]


async def retrieve_rag_context(
    repository: ResourceTaskRepository,
    ai_client: AIClient,
    course_id: str,
    query: str,
    user_id: str | None = None,
    notebook_id: str | None = None,
    document_ids: list[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    document_map: dict[str, RAGDocument] = {}
    if user_id or notebook_id or document_ids:
        documents = await resolve_rag_documents(
            repository=repository,
            course_id=course_id,
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
        )
        if not documents:
            return []
        document_map = {document.document_id: document for document in documents}
        document_ids = [document.document_id for document in documents]

    embeddings = await ai_client.embed_texts([query], embedding_domain="query")
    if not embeddings:
        return []

    results = await repository.search_rag_chunks(
        course_id=course_id,
        query_embedding=embeddings[0],
        document_ids=document_ids,
        limit=limit,
    )
    context: list[dict[str, Any]] = []
    for chunk, score in results:
        document = document_map.get(chunk.document_id)
        context.append({
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "source_id": document.source_id if document else chunk.document_id,
            "source_title": document.source_title if document else chunk.document_id,
            "notebook_id": document.notebook_id if document else None,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "score": score,
        })
    return context
