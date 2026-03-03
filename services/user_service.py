"""사용자 관리 서비스 (사용자 추가, 보안키 발송, 암호 초기화)"""

import json
import os
import random
import string
import smtplib
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "settings.json")


def _generate_security_key(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        encoded = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except Exception:
        return False


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_users() -> List[dict]:
    data = load_settings()
    users = data.get("users", [])
    result = []
    for u in users:
        sk = u.get("security_key", "")
        pc = u.get("password_changed", False)
        result.append({
            "email": u["email"],
            "security_key_masked": "—" if pc else "****-****-****",
            "has_security_key": bool(sk) and not pc,
            "password_changed": pc,
            "active": u.get("active", True),
        })
    return result


def add_user(email: str) -> bool:
    data = load_settings()
    users = data.get("users", [])
    for u in users:
        if u["email"] == email:
            return False
    security_key = _generate_security_key()
    users.append({
        "email": email,
        "password_hash": "",
        "security_key": security_key,
        "password_changed": False,
        "active": True,
    })
    data["users"] = users
    save_settings(data)
    return True


def delete_user(email: str) -> bool:
    data = load_settings()
    users = data.get("users", [])
    new_users = [u for u in users if u["email"] != email]
    if len(new_users) == len(users):
        return False
    data["users"] = new_users
    save_settings(data)
    return True


def reset_user_password(email: str) -> Optional[str]:
    """비밀번호 초기화 + 신규 보안키 재생성. 이메일 발송 없음."""
    data = load_settings()
    users = data.get("users", [])
    for u in users:
        if u["email"] == email:
            new_key = _generate_security_key()
            u["password_hash"] = ""
            u["security_key"] = new_key
            u["password_changed"] = False
            data["users"] = users
            save_settings(data)
            return new_key
    return None


def get_user_security_key(email: str) -> Optional[str]:
    """평문 보안키 조회 (password_changed: false 상태만)"""
    data = load_settings()
    for u in data.get("users", []):
        if u["email"] == email:
            if not u.get("password_changed", False):
                return u.get("security_key", "") or None
    return None


def verify_user(email: str, password: str) -> Optional[dict]:
    """사용자 인증. 보안키 또는 변경된 암호로 검증."""
    data = load_settings()
    for u in data.get("users", []):
        if u["email"] == email and u.get("active", True):
            # 암호 미설정 상태: 보안키로 로그인
            if not u.get("password_hash"):
                sk = u.get("security_key", "")
                if sk and password == sk:
                    return {"email": email, "password_changed": u.get("password_changed", False)}
            else:
                if _verify_password(password, u["password_hash"]):
                    return {"email": email, "password_changed": u.get("password_changed", False)}
    return None


def set_user_password(email: str, current_password: str, new_password: str) -> bool:
    """사용자 최초 암호 설정"""
    data = load_settings()
    users = data.get("users", [])
    for u in users:
        if u["email"] == email and u.get("active", True):
            # 현재 암호 검증 (보안키 또는 기존 암호)
            if not u.get("password_hash"):
                sk = u.get("security_key", "")
                if not (sk and current_password == sk):
                    return False
            else:
                if not _verify_password(current_password, u["password_hash"]):
                    return False
            u["password_hash"] = _hash_password(new_password)
            u["password_changed"] = True
            u["security_key"] = ""
            data["users"] = users
            save_settings(data)
            return True
    return False


def send_security_key_email(email: str) -> dict:
    """보안키 이메일 발송. SMTP 미설정 시 콘솔 출력."""
    security_key = get_user_security_key(email)
    if not security_key:
        return {"success": False, "error": "보안키가 없거나 이미 암호가 변경된 사용자입니다."}

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "")

    if not smtp_host or not smtp_user or not smtp_password:
        print("=" * 50)
        print(f"  [MANA] 사용자 보안키 (이메일 발송 실패)")
        print(f"  이메일: {email}")
        print(f"  보안키: {security_key}")
        print("=" * 50)
        return {"success": False, "console": True, "error": "SMTP 미설정"}

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from or smtp_user
        msg["To"] = email
        msg["Subject"] = "[MANA] 접속 보안키 안내"
        body = f"""안녕하세요.

MANA(캡틴 FLOW) 서비스 접속을 위한 보안키를 안내드립니다.

접속 이메일: {email}
보안키: {security_key}

위 보안키로 로그인 후 반드시 새 암호를 설정해 주세요.

감사합니다.
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from or smtp_user, email, msg.as_string())

        return {"success": True}
    except Exception as e:
        print(f"  [MANA] 이메일 발송 실패: {e}")
        print(f"  이메일: {email}, 보안키: {security_key}")
        return {"success": False, "console": True, "error": str(e)}
