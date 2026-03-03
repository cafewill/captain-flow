"""Claude / OpenAI / Gemini API 호출 서비스 (모델별 분기)"""

import os
from typing import AsyncGenerator

from config.presets import AI_MODELS, RESPONSE_FORMATS, RESPONSE_LANGUAGES
from services.auth_service import load_settings


def _build_system_prompt(response_format: str, response_language: str) -> str:
    parts = []
    fmt = RESPONSE_FORMATS.get(response_format, "")
    if fmt:
        parts.append(fmt)
    lang = RESPONSE_LANGUAGES.get(response_language, "")
    if lang:
        parts.append(lang)
    return " ".join(parts) if parts else "기본 마크다운 형식으로 응답해줘."


def _build_user_prompt(tech_stack: str, request_text: str) -> str:
    if tech_stack and tech_stack != "지정 안 함":
        return f"[기술 스택: {tech_stack}]\n\n{request_text}"
    return request_text


async def stream_response(
    ai_model: str,
    question_type: str,
    tech_stack: str,
    request_text: str,
    response_format: str,
    response_language: str,
) -> AsyncGenerator[str, None]:
    model_info = AI_MODELS.get(ai_model)
    if not model_info:
        yield f"data: {{\"error\": \"알 수 없는 모델: {ai_model}\"}}\n\n"
        return

    provider = model_info["provider"]
    model_id = model_info["model_id"]

    settings = load_settings()

    system_prompt = _build_system_prompt(response_format, response_language)
    user_prompt = _build_user_prompt(tech_stack, request_text)

    if provider == "anthropic":
        api_key = settings.get("anthropic_key", "")
        if not api_key:
            yield 'data: {"error": "설정 관리에서 Claude API KEY를 먼저 등록하세요."}\n\n'
            return
        async for chunk in _stream_anthropic(api_key, model_id, system_prompt, user_prompt):
            yield chunk

    elif provider == "openai":
        api_key = settings.get("openai_key", "")
        if not api_key:
            yield 'data: {"error": "설정 관리에서 OpenAI API KEY를 먼저 등록하세요."}\n\n'
            return
        async for chunk in _stream_openai(api_key, model_id, system_prompt, user_prompt):
            yield chunk

    elif provider == "google":
        api_key = settings.get("gemini_key", "")
        if not api_key:
            yield 'data: {"error": "설정 관리에서 Gemini API KEY를 먼저 등록하세요."}\n\n'
            return
        async for chunk in _stream_gemini(api_key, model_id, system_prompt, user_prompt):
            yield chunk

    else:
        yield f'data: {{"error": "지원하지 않는 공급사입니다: {provider}"}}\n\n'


async def _stream_anthropic(api_key: str, model_id: str, system_prompt: str, user_prompt: str):
    import json
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    try:
        with client.messages.stream(
            model=model_id,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                if text:
                    yield f"data: {json.dumps({'delta': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


async def _stream_openai(api_key: str, model_id: str, system_prompt: str, user_prompt: str):
    import json
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model_id,
            stream=True,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        for event in response:
            if event.type == "response.output_text.delta":
                if event.delta:
                    yield f"data: {json.dumps({'delta': event.delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


async def _stream_gemini(api_key: str, model_id: str, system_prompt: str, user_prompt: str):
    import json
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content_stream(
            model=model_id,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        for chunk in response:
            if chunk.text:
                yield f"data: {json.dumps({'delta': chunk.text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
