"""Weaviate-backed RAG service."""

from __future__ import annotations

from typing import Callable, List, Optional

import weaviate
from weaviate.auth import AuthApiKey
from openai import AsyncOpenAI

from backend.config.settings import settings, get_optimization_config
from backend.database import SessionLocal
from backend.database.repositories import DocumentRepository
from backend.ingestion.url_ingestor import IngestionResult, URLIngestor


class RAGService:
    def __init__(
        self,
        client: Optional[weaviate.Client] = None,
        embedding_client: Optional[AsyncOpenAI] = None,
        ingestor: Optional[URLIngestor] = None,
        session_factory: Optional[Callable[[], object]] = None,
        document_repository_cls: Optional[type[DocumentRepository]] = DocumentRepository,
    ) -> None:
        auth_config = None
        if settings.weaviate_api_key:
            auth_config = AuthApiKey(api_key=settings.weaviate_api_key)
        self.client = client or weaviate.Client(settings.weaviate_url, auth_client_secret=auth_config)
        self.ingestor = ingestor or URLIngestor()
        self.embedding_client = embedding_client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.session_factory = session_factory or SessionLocal
        self.document_repository_cls = document_repository_cls

    async def ingest_url(self, url: str) -> None:
        ingestion = await self.ingestor.ingest(url)
        await self._ensure_schema()
        if self.document_repository_cls is not None:
            session = self.session_factory()
            try:
                repo = self.document_repository_cls(session)
                repo.upsert_document(url, ingestion.checksum, ingestion.title)
            finally:
                close = getattr(session, "close", None)
                if callable(close):
                    close()
        vectors = await self._embed_chunks([chunk.text for chunk in ingestion.chunks])
        with self.client.batch as batch:
            for chunk, vector in zip(ingestion.chunks, vectors):
                batch.add_data_object(
                    data_object={
                        "text": chunk.text,
                        "source_url": chunk.metadata["source_url"],
                        "chunk_index": chunk.metadata["chunk_index"],
                        "document_checksum": chunk.metadata["document_checksum"],
                    },
                    class_name="DocumentChunk",
                    vector=vector,
                )

    async def _embed_chunks(self, texts: List[str]) -> List[List[float]]:
        if not self.embedding_client:
            raise RuntimeError("Embedding client not configured")
        response = await self.embedding_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def retrieve(
        self, query: str, top_k: Optional[int] = None, optimization_level: Optional[str] = None
    ) -> List[str]:
        """
        Retrieve relevant context chunks for a query.

        Args:
            query: The search query
            top_k: Number of chunks to retrieve (overrides optimization level)
            optimization_level: Optimization level (quality/balanced_quality/balanced/balanced_speed/speed)

        Returns:
            List of relevant text chunks
        """
        # Determine top_k based on optimization level if not explicitly provided
        if top_k is None:
            if optimization_level:
                config = get_optimization_config(optimization_level)
                top_k = config.rag_top_k
            else:
                top_k = 5  # Default

        # Skip RAG entirely if top_k is 0 (speed optimization)
        if top_k == 0:
            return []

        result = (
            self.client.query.get("DocumentChunk", ["text", "source_url"])
            .with_near_text({"concepts": [query]})
            .with_limit(top_k)
            .do()
        )
        hits = result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
        return [hit.get("text", "") for hit in hits]

    async def _ensure_schema(self) -> None:
        schema = self.client.schema.get()
        class_names = [cls.get("class") for cls in schema.get("classes", [])]
        if "DocumentChunk" not in class_names:
            self.client.schema.create_class(
                {
                    "class": "DocumentChunk",
                    "properties": [
                        {"name": "text", "dataType": ["text"]},
                        {"name": "source_url", "dataType": ["text"]},
                        {"name": "chunk_index", "dataType": ["int"]},
                        {"name": "document_checksum", "dataType": ["text"]},
                    ],
                    "vectorizer": "none",
                }
            )

