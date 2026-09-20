from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.schema import ChatRequest, ChatResponse
from backend.app.core.logging import logger

router = APIRouter()

_pipeline = None

def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline

def get_pipeline():
    if not _pipeline:
        raise HTTPException(status_code=503, detail="RAG Pipeline initializing. Please retry in a moment.")
    return _pipeline

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, pipeline=Depends(get_pipeline)):
    """
    Main endpoint for student and visitor inquiries.
    Supports multi-turn context (conversational query rewriting),
    multi-signal confidence gate, and output validation.
    """
    try:
        response = await pipeline.answer_query(
            request.message,
            language=request.language,
            history=request.history
        )
        return response
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
