"""콤보박스 프리셋 데이터"""

AI_MODELS = {
    "Claude Opus 4.6": {"provider": "anthropic", "model_id": "claude-opus-4-6"},
    "Claude Sonnet 4.6": {"provider": "anthropic", "model_id": "claude-sonnet-4-6"},
    "Claude Sonnet (2025-05-14)": {"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
    "Claude Haiku 4.5": {"provider": "anthropic", "model_id": "claude-haiku-4-5-20251001"},
    "GPT-5.2 (OpenAI)": {"provider": "openai", "model_id": "gpt-5.2"},
    "GPT-5-mini (OpenAI)": {"provider": "openai", "model_id": "gpt-5-mini"},
    "Gemini 2.5 Flash (Google)": {"provider": "google", "model_id": "gemini-2.5-flash"},
    "Gemini 2.5 Pro (Google)": {"provider": "google", "model_id": "gemini-2.5-pro"},
}

QUESTION_TYPES = {
    "code_review": "코드 리뷰",
    "code_gen": "코드 생성",
    "error_fix": "오류 해결",
    "refactor": "리팩토링",
    "unit_test": "단위 테스트",
    "db_design": "DB 설계",
    "api_design": "API 설계",
    "explain": "개념 설명",
    "direct": "직접 입력",
}

TECH_STACKS = [
    "지정 안 함",
    "Python / FastAPI",
    "Java / Spring Boot",
    "JavaScript / Node.js",
    "SQL / PostgreSQL",
    "SQL / MySQL",
    "HTML / CSS / JS",
    "React / Vue.js",
    "Docker / K8s",
    "Git / CI-CD",
]

RESPONSE_FORMATS = {
    "기본 (마크다운)": "기본 마크다운 형식으로 응답해줘.",
    "코드 위주": "설명 최소화, 코드 블록 중심으로 응답해줘.",
    "단계별 설명": "번호를 붙여 단계별로 설명해줘.",
    "간결하게": "핵심만 3줄 이내로 요약해서 응답해줘.",
    "상세하게": "배경 지식부터 상세하게 설명해줘.",
    "표/비교 형식": "비교 항목은 표(table)로 정리해줘.",
}

RESPONSE_LANGUAGES = {
    "자동 (AI 판단)": "",
    "영어": "Respond in English only.",
    "한국어": "반드시 한국어로만 응답해줘.",
    "일본어": "Respond in Japanese only.",
    "중국어 (간체)": "Respond in Simplified Chinese only (Mainland China).",
    "중국어 (번체-대만)": "Respond in Traditional Chinese only (Taiwan).",
    "중국어 (번체-홍콩)": "Respond in Traditional Chinese only (Hong Kong).",
}
