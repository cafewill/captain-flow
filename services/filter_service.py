"""민감정보 필터링 서비스 (룰셋, 스캔, 마스킹, 감사 로그)"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "settings.json")
AUDIT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "security_events.jsonl")

KST = timezone(timedelta(hours=9))

# 기본 룰셋 (하드코딩)
DEFAULT_RULES = [
    {
        "name": "ANTHROPIC_KEY",
        "pattern": r"sk-ant-[A-Za-z0-9\-]{20,}",
        "action": "block",
        "mask": lambda m: m[:10] + "****...****",
    },
    {
        "name": "OPENAI_KEY",
        "pattern": r"sk-[A-Za-z0-9]{20,}",
        "action": "block",
        "mask": lambda m: "sk-****...****",
    },
    {
        "name": "GEMINI_KEY",
        "pattern": r"AIza[A-Za-z0-9\-_]{35}",
        "action": "block",
        "mask": lambda m: "AIza****...****",
    },
    {
        "name": "BEARER_TOKEN",
        "pattern": r"Bearer\s+[A-Za-z0-9\-_.~+\/]+=*",
        "action": "mask",
        "mask": lambda m: "Bearer [REDACTED]",
    },
    {
        "name": "JWT_TOKEN",
        "pattern": r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]*",
        "action": "mask",
        "mask": lambda m: "[JWT_REDACTED]",
    },
    {
        "name": "PRIVATE_KEY",
        "pattern": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "action": "block",
        "mask": lambda m: "[PRIVATE_KEY_REDACTED]",
    },
    {
        "name": "DB_CONN_STRING",
        "pattern": r"(mysql|postgresql|mongodb):\/\/[^:]+:[^@]+@",
        "action": "mask",
        "mask": lambda m: "[DB_CONN_REDACTED]",
    },
    {
        "name": "COOKIE_HEADER",
        "pattern": r"Cookie:\s*.+=.+",
        "action": "mask",
        "mask": lambda m: "Cookie: [REDACTED]",
    },
    {
        "name": "PASSWORD_KEYWORD",
        "pattern": r"(?i)(password|passwd|pwd|pw|pass|secret|secretkey|secretword|암호|비번|비밀번호|보안키|패스워드|패쓰워드|パスワード|密码|口令)\s*[=:]\s*\S+",
        "action": "mask",
        "mask": lambda m: re.sub(r"([=:])\s*\S+", r"\1[REDACTED]", m),
    },
    {
        "name": "AWS_ACCESS_KEY",
        "pattern": r"AKIA[A-Z0-9]{16}",
        "action": "block",
        "mask": lambda m: "AKIA****...****",
    },
    {
        "name": "USER_CREDENTIAL",
        "pattern": r"(?i)(user(?:name|id|pass(?:word)?|pw)?)\s*[=:/]\s*\S+",
        "action": "mask",
        "mask": lambda m: re.sub(r"([=:/])\s*\S+", r"\1[REDACTED]", m),
    },
    {
        "name": "ACCOUNT_KEYWORD",
        "pattern": r"(?i)(로그인|아이디|비번|비밀번호|계정|사용자|login|id|user(?:name|id)?|account|pass(?:word)?|pw|secret|ログイン|アカウント|ユーザー|账号|账户|用户名)\s*[=:/]\s*\S+",
        "action": "mask",
        "mask": lambda m: re.sub(r"([=:/])\s*\S+", r"\1[REDACTED]", m),
    },
    {
        "name": "ACCOUNT_BLOCK",
        "pattern": r"(?i)계정\s*[:/]\s*\S+\s*/\s*\S+",
        "action": "mask",
        "mask": lambda m: "계정: [REDACTED]",
    },
]

# 고위험 룰 (역방향 필터용)
HIGH_RISK_RULE_NAMES = {"ANTHROPIC_KEY", "OPENAI_KEY", "GEMINI_KEY", "AWS_ACCESS_KEY", "PRIVATE_KEY"}


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings_file(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_filter_settings() -> dict:
    data = load_settings()
    return data.get("sensitivity_filter", {
        "enabled": False,
        "level": 1,
        "custom_rules": [],
        "allowlist": []
    })


def save_filter_settings(settings: dict):
    data = load_settings()
    data["sensitivity_filter"] = settings
    save_settings_file(data)


def _is_allowlisted(text: str, allowlist: List[str]) -> bool:
    for item in allowlist:
        if item and item in text:
            return True
    return False


def scan_text(text: str) -> List[dict]:
    cfg = get_filter_settings()
    allowlist = cfg.get("allowlist", [])
    results = []
    matched_rules = set()

    # 기본 룰셋 스캔
    for rule in DEFAULT_RULES:
        if rule["name"] in matched_rules:
            continue
        matches = re.findall(rule["pattern"], text)
        if matches:
            # allowlist 체크
            skip = False
            for m in (matches if isinstance(matches[0], str) else [m[0] for m in matches]):
                if _is_allowlisted(m if isinstance(m, str) else str(m), allowlist):
                    skip = True
                    break
            if not skip:
                results.append({
                    "rule": rule["name"],
                    "action": rule["action"],
                    "count": len(matches),
                })
                matched_rules.add(rule["name"])

    # 커스텀 룰 스캔
    for custom in cfg.get("custom_rules", []):
        try:
            matches = re.findall(custom["pattern"], text)
            if matches:
                results.append({
                    "rule": custom["name"],
                    "action": custom.get("action", "warn"),
                    "count": len(matches),
                })
        except re.error:
            pass

    return results


def mask_text(text: str) -> str:
    cfg = get_filter_settings()
    allowlist = cfg.get("allowlist", [])
    result = text

    for rule in DEFAULT_RULES:
        def replacer(m, rule=rule):
            matched = m.group(0)
            if _is_allowlisted(matched, allowlist):
                return matched
            try:
                return rule["mask"](matched)
            except Exception:
                return "[REDACTED]"
        result = re.sub(rule["pattern"], replacer, result)

    for custom in cfg.get("custom_rules", []):
        action = custom.get("action", "warn")
        if action in ("mask", "block"):
            try:
                result = re.sub(custom["pattern"], "[REDACTED]", result)
            except re.error:
                pass

    return result


def apply_response_filter(text: str) -> str:
    """AI 응답에 역방향 필터 적용 (고위험 룰 5종만)"""
    cfg = get_filter_settings()
    if not cfg.get("enabled", False):
        return text

    result = text
    for rule in DEFAULT_RULES:
        if rule["name"] not in HIGH_RISK_RULE_NAMES:
            continue

        def replacer(m, rule=rule):
            matched = m.group(0)
            try:
                return rule["mask"](matched)
            except Exception:
                return "[REDACTED]"
        result = re.sub(rule["pattern"], replacer, result)

    return result


def write_audit_log(level: int, results: List[dict], action: str):
    """감사 로그 기록 (메타 정보만, 원문 저장 금지)"""
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    entry = {
        "ts": datetime.now(KST).isoformat(),
        "user": "admin",
        "level": level,
        "rules": [r["rule"] for r in results],
        "count": len(results),
        "action": action,
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
