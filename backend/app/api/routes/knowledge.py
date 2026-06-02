from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.ai_errors import AIServiceError
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.knowledge import (
    DocumentImportResponse,
    KnowledgeCreate,
    KnowledgeResponse,
    KnowledgeStatsResponse,
    KnowledgeUpdate,
)
from app.services.document_import_service import import_document_to_knowledge
from app.services.embedding.factory import get_embedding_client
from app.services.knowledge_service import (
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    get_knowledge_category_stats,
    list_knowledge,
    update_knowledge,
)
from app.services.upload_storage_service import delete_uploaded_file, save_uploaded_file

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=List[KnowledgeResponse])
def list_items(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list:
    return list_knowledge(db, category=category, skip=skip, limit=limit)


@router.get("/stats", response_model=KnowledgeStatsResponse)
def get_stats(db: Session = Depends(get_db)) -> dict:
    return get_knowledge_category_stats(db)


@router.post("", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await create_knowledge(db, payload, get_embedding_client(settings))
    except AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/import", response_model=DocumentImportResponse, status_code=status.HTTP_201_CREATED)
async def import_document(
    category: str = Form(...),
    source: str = Form(default="上传文档"),
    chunking_method: str = Form(default="fixed_size"),
    chunk_size: int = Form(default=1200),
    chunk_overlap: int = Form(default=150),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    stored_file_path = save_uploaded_file(file.filename, data, settings.upload_dir_path)
    try:
        items = await import_document_to_knowledge(
            db=db,
            filename=file.filename or "uploaded-document",
            data=data,
            category=category,
            source=source,
            document_path=str(stored_file_path),
            chunking_method=chunking_method,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_client=get_embedding_client(settings),
        )
    except ValueError as exc:
        delete_uploaded_file(stored_file_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIServiceError as exc:
        delete_uploaded_file(stored_file_path)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        delete_uploaded_file(stored_file_path)
        raise

    return {
        "filename": file.filename or "uploaded-document",
        "stored_file_path": str(stored_file_path),
        "imported_count": len(items),
        "items": items,
    }


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
def get_item(knowledge_id: int, db: Session = Depends(get_db)):
    item = get_knowledge(db, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return item


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_item(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    item = get_knowledge(db, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    try:
        return await update_knowledge(db, item, payload, get_embedding_client(settings))
    except AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
):
    item = get_knowledge(db, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    delete_knowledge(db, item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
