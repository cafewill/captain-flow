"""AI API 연동 라우터"""

import json
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.request_model import AskRequest
from services.ai_service import stream_response
from services.auth_service import decode_token
from services.filter_service import get_filter_settings, scan_text, mask_text, write_audit_log
from config.presets import AI_MODELS, QUESTION_TYPES, TECH_STACKS, RESPONSE_FORMATS, RESPONSE_LANGUAGES

router = APIRouter(prefix="/api/ai", tags=["ai"])
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return payload


@router.post("/ask")
async def ask(req: AskRequest, user=Depends(get_current_user)):
    # 민감정보 필터 게이트
    filter_cfg = get_filter_settings()
    if filter_cfg.get("enabled", False):
        level = filter_cfg.get("level", 1)
        results = scan_text(req.request_text)
        if results:
            write_audit_log(level, results, "block" if level == 3 else ("mask" if level == 2 else "warn"))
            if level == 3:
                raise HTTPException(status_code=400, detail="민감정보 감지로 전송이 차단되었습니다.")
            if level == 2:
                req.request_text = mask_text(req.request_text)

    async def generate():
        async for chunk in stream_response(
            ai_model=req.ai_model,
            question_type=req.question_type,
            tech_stack=req.tech_stack,
            request_text=req.request_text,
            response_format=req.response_format,
            response_language=req.response_language,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/presets")
async def get_presets():
    return {
        "ai_models": list(AI_MODELS.keys()),
        "question_types": QUESTION_TYPES,
        "tech_stacks": TECH_STACKS,
        "response_formats": list(RESPONSE_FORMATS.keys()),
        "response_languages": list(RESPONSE_LANGUAGES.keys()),
    }
