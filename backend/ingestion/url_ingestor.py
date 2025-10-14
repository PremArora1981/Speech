"""URL ingestion pipeline for RAG."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup


@dataclass
class Chunk:
    text: str
    metadata: dict


@dataclass
class IngestionResult:
    title: Optional[str]
    checksum: str
    chunks: List[Chunk]


class URLIngestor:
    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 100,
        embedding_model: Optional[str] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.embedding_model = embedding_model

    async def ingest(self, url: str) -> IngestionResult:
        html = await self._fetch(url)
        text, title = self._extract_text(html)
        checksum = hashlib.sha256(text.encode()).hexdigest()
        chunks = self._chunk_text(text, url, checksum)
        return IngestionResult(title=title, checksum=checksum, chunks=chunks)

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
            response.raise_for_status()
            return response.text

    def _extract_text(self, html: str) -> tuple[str, Optional[str]]:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = " ".join(soup.stripped_strings)
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        return text, title

    def _chunk_text(self, text: str, url: str, checksum: str) -> List[Chunk]:
        words = text.split()
        chunks = []
        step = self.chunk_size - self.overlap
        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size]
            if not chunk_words:
                continue
            chunk_text = " ".join(chunk_words)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata={
                        "source_url": url,
                        "chunk_index": len(chunks),
                        "chunk_checksum": hashlib.sha256(chunk_text.encode()).hexdigest(),
                        "document_checksum": checksum,
                    },
                )
            )
        return chunks

