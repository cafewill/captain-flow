"""Pydantic 요청/응답 모델"""

from pydantic import BaseModel
from typing import Optional, List


class AskRequest(BaseModel):
    ai_model: str
    question_type: str = "direct"
    tech_stack: str = "지정 안 함"
    request_text: str
    response_format: str = "기본 (마크다운)"
    response_language: str = "자동 (AI 판단)"


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ApiKeyRequest(BaseModel):
    anthropic_key: str = ""
    openai_key: str = ""
    gemini_key: str = ""


class CustomRule(BaseModel):
    name: str
    pattern: str
    action: str  # warn / mask / block


class FilterSettingsRequest(BaseModel):
    enabled: bool = False
    level: int = 1
    custom_rules: List[CustomRule] = []
    allowlist: List[str] = []


class AddUserRequest(BaseModel):
    email: str


class UserChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
