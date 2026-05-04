from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Literature
from ..schemas import AgentStatusResponse, AgentSuggestRequest, AgentSuggestResponse
from ..services.agent_service import AgentService
from ..services.agent_tools import read_text_from_path
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])
service = AgentService()


@router.post("/suggest", response_model=AgentSuggestResponse)
def suggest(payload: AgentSuggestRequest, db: Session = Depends(get_db)):
    text = payload.text or ""
    filename = payload.filename
    literature_id = payload.literature_id

    if literature_id:
        literature = db.get(Literature, literature_id)
        if not literature:
            raise HTTPException(status_code=404, detail="Literature not found")
        if not text:
            text = literature.content_text or ""
        if not text and literature.file_path:
            text = read_text_from_path(Path(literature.file_path))
        if not filename:
            filename = literature.file_name or None
        if not filename and literature.file_path:
            filename = Path(literature.file_path).name

    if not text and not filename:
        raise HTTPException(status_code=400, detail="No text or filename provided")

    result = service.suggest_metadata(
        text=text,
        filename=filename,
        literature_id=literature_id,
    )
    return AgentSuggestResponse(**result)


@router.get("/status", response_model=AgentStatusResponse)
def status():
    return service.get_status()
