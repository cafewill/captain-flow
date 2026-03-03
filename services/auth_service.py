"""관리자 인증 서비스 (보안키 생성, 암호 변경, API KEY 관리)"""

import json
import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "settings.json")
SECRET_KEY = os.getenv("SECRET_KEY", "mana-default-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 4


def _hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        encoded = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except Exception:
        return False


def _generate_security_key(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_settings():
    """최초 실행 시 settings.json 생성 및 보안키 콘솔 출력"""
    if not os.path.exists(SETTINGS_PATH):
        security_key = _generate_security_key()
        password_hash = _hash_password(security_key)
        data = {
            "admin_password_hash": password_hash,
            "security_key": security_key,
            "password_changed": False,
            "anthropic_key": "",
            "openai_key": "",
            "gemini_key": "",
            "users": [],
            "sensitivity_filter": {
                "enabled": False,
                "level": 1,
                "custom_rules": [],
                "allowlist": []
            }
        }
        save_settings(data)
        _print_security_key(security_key)
    else:
        data = load_settings()
        if not data.get("password_changed", False):
            security_key = data.get("security_key", "")
            if security_key:
                _print_security_key(security_key)


def _print_security_key(key: str):
    print("=" * 60)
    print("  MANA 최초 실행 — 관리자 보안키")
    print(f"  아이디 : admin")
    print(f"  보안키 : {key}")
    print("  ⚠️  반드시 웹 접속 후 설정 관리에서 암호를 변경하세요!")
    print("=" * 60)


def verify_admin(password: str) -> bool:
    data = load_settings()
    hashed = data.get("admin_password_hash", "")
    if not hashed:
        return False
    return _verify_password(password, hashed)


def change_password(current_password: str, new_password: str) -> bool:
    data = load_settings()
    hashed = data.get("admin_password_hash", "")
    if not hashed or not _verify_password(current_password, hashed):
        return False
    data["admin_password_hash"] = _hash_password(new_password)
    data["password_changed"] = True
    data["security_key"] = ""
    save_settings(data)
    return True


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_api_keys() -> dict:
    data = load_settings()
    return {
        "anthropic_key": data.get("anthropic_key", ""),
        "openai_key": data.get("openai_key", ""),
        "gemini_key": data.get("gemini_key", ""),
    }


def save_api_keys(anthropic_key: str, openai_key: str, gemini_key: str):
    data = load_settings()
    if anthropic_key:
        data["anthropic_key"] = anthropic_key
    if openai_key:
        data["openai_key"] = openai_key
    if gemini_key:
        data["gemini_key"] = gemini_key
    save_settings(data)


def mask_api_key(key: str, prefix: str = "") -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return prefix + "****"
    return key[:len(prefix) + 4] + "****...****"
