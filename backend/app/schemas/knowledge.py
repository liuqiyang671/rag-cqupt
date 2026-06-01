from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBasePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    source: str = Field(default="校内知识库", max_length=255)
    document_name: Optional[str] = Field(default=None, max_length=255)
    document_path: Optional[str] = Field(default=None, max_length=500)
    chunk_index: Optional[int] = Field(default=None, ge=1)
    chunk_total: Optional[int] = Field(default=None, ge=1)
    chunking_method: Optional[str] = Field(default=None, max_length=50)


class KnowledgeCreate(KnowledgeBasePayload):
    pass


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    content: Optional[str] = Field(default=None, min_length=1)
    source: Optional[str] = Field(default=None, max_length=255)
    document_name: Optional[str] = Field(default=None, max_length=255)
    document_path: Optional[str] = Field(default=None, max_length=500)
    chunk_index: Optional[int] = Field(default=None, ge=1)
    chunk_total: Optional[int] = Field(default=None, ge=1)
    chunking_method: Optional[str] = Field(default=None, max_length=50)


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    category: str
    content: str
    source: str
    document_name: Optional[str] = None
    document_path: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_total: Optional[int] = None
    chunking_method: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrievedKnowledge(BaseModel):
    id: int
    title: str
    category: str
    content: str
    source: str
    citation_index: Optional[int] = None
    relevance_score: Optional[float] = None
    match_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentImportResponse(BaseModel):
    filename: str
    stored_file_path: str
    imported_count: int
    items: List[KnowledgeResponse]
