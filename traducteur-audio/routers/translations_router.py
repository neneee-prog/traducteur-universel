# traducteur-audio/routers/translations_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.firestore_db import create_translation, list_translations

router = APIRouter(prefix="/api/translations", tags=["translations"])

class TranslationRequest(BaseModel):
    text: str

@router.post("/")
async def save_translation(req: TranslationRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    doc_id = create_translation(req.text)
    return {"message": "Traduction enregistrée", "doc_id": doc_id}

@router.get("/")
async def get_translations():
    data = list_translations()
    return {"translations": data}
