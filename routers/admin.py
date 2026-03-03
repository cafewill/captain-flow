"""관리자 인증, 설정 관리, 사용자 관리 라우터"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.request_model import (
    AdminLoginRequest, ChangePasswordRequest, ApiKeyRequest,
    FilterSettingsRequest, AddUserRequest, UserLoginRequest, UserChangePasswordRequest
)
from services.auth_service import (
    verify_admin, change_password, create_access_token,
    decode_token, get_api_keys, save_api_keys, mask_api_key
)
from services.filter_service import get_filter_settings, save_filter_settings
from services.user_service import (
    get_users, add_user, delete_user, reset_user_password,
    get_user_security_key, verify_user, set_user_password, send_security_key_email
)

router = APIRouter(tags=["admin"])
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return payload


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return user


# ──────────────────────────────
# 관리자 로그인
# ──────────────────────────────
@router.post("/api/admin/login")
async def admin_login(req: AdminLoginRequest):
    if req.username != "admin":
        raise HTTPException(status_code=401, detail="아이디 또는 암호가 올바르지 않습니다.")
    if not verify_admin(req.password):
        raise HTTPException(status_code=401, detail="아이디 또는 암호가 올바르지 않습니다.")
    token = create_access_token("admin", "admin")
    return {"access_token": token, "token_type": "bearer", "role": "admin"}


# ──────────────────────────────
# 관리자 암호 변경
# ──────────────────────────────
@router.post("/api/admin/change-password")
async def admin_change_password(req: ChangePasswordRequest, user=Depends(require_admin)):
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="새 암호는 8자 이상이어야 합니다.")
    if not change_password(req.current_password, req.new_password):
        raise HTTPException(status_code=400, detail="현재 암호가 올바르지 않습니다.")
    return {"message": "암호가 변경되었습니다."}


# ──────────────────────────────
# API KEY 관리
# ──────────────────────────────
@router.get("/api/admin/apikeys")
async def get_apikeys(user=Depends(require_admin)):
    keys = get_api_keys()
    return {
        "anthropic_key": mask_api_key(keys["anthropic_key"], "sk-ant-"),
        "openai_key": mask_api_key(keys["openai_key"], "sk-"),
        "gemini_key": mask_api_key(keys["gemini_key"], "AIza"),
    }


@router.post("/api/admin/apikeys")
async def save_apikeys(req: ApiKeyRequest, user=Depends(require_admin)):
    save_api_keys(req.anthropic_key, req.openai_key, req.gemini_key)
    return {"message": "API KEY가 저장되었습니다."}


# ──────────────────────────────
# 민감정보 필터
# ──────────────────────────────
@router.get("/api/admin/filter")
async def get_filter(user=Depends(require_admin)):
    return get_filter_settings()


@router.post("/api/admin/filter")
async def save_filter(req: FilterSettingsRequest, user=Depends(require_admin)):
    data = {
        "enabled": req.enabled,
        "level": req.level,
        "custom_rules": [r.model_dump() for r in req.custom_rules],
        "allowlist": req.allowlist,
    }
    save_filter_settings(data)
    return {"message": "민감정보 필터 설정이 저장되었습니다."}


# ──────────────────────────────
# 사용자 관리
# ──────────────────────────────
@router.get("/api/admin/users")
async def list_users(user=Depends(require_admin)):
    return {"users": get_users()}


@router.post("/api/admin/users")
async def create_user(req: AddUserRequest, user=Depends(require_admin)):
    if not add_user(req.email):
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")
    return {"message": "사용자가 추가되었습니다. 목록에서 [보안키 발송]을 클릭하여 보안키를 발송하세요."}


@router.delete("/api/admin/users/{email}")
async def remove_user(email: str, user=Depends(require_admin)):
    if not delete_user(email):
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {"message": "사용자가 삭제되었습니다."}


@router.post("/api/admin/users/{email}/reset")
async def reset_user(email: str, user=Depends(require_admin)):
    result = reset_user_password(email)
    if result is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {"message": "비밀번호가 초기화되었습니다. [보안키 발송]을 클릭하여 신규 보안키를 발송하세요."}


@router.post("/api/admin/users/{email}/send-key")
async def send_key(email: str, user=Depends(require_admin)):
    result = send_security_key_email(email)
    if result.get("success"):
        return {"message": "보안키가 발송되었습니다."}
    else:
        if result.get("console"):
            return {"message": "이메일 발송 실패 — 콘솔을 확인하세요.", "console_key": True}
        raise HTTPException(status_code=400, detail=result.get("error", "발송 실패"))


@router.get("/api/admin/users/{email}/security-key")
async def get_security_key(email: str, user=Depends(require_admin)):
    key = get_user_security_key(email)
    if not key:
        raise HTTPException(status_code=404, detail="보안키가 없거나 이미 암호가 변경된 사용자입니다.")
    return {"email": email, "security_key": key}


# ──────────────────────────────
# 사용자 로그인 / 암호 변경
# ──────────────────────────────
@router.post("/api/user/login")
async def user_login(req: UserLoginRequest):
    result = verify_user(req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="아이디 또는 암호가 올바르지 않습니다.")
    token = create_access_token(req.username, "user")
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "user",
        "password_changed": result["password_changed"],
    }


@router.post("/api/user/change-password")
async def user_change_password(req: UserChangePasswordRequest, user=Depends(get_current_user)):
    email = user.get("sub")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="새 암호는 8자 이상이어야 합니다.")
    if not set_user_password(email, req.current_password, req.new_password):
        raise HTTPException(status_code=400, detail="현재 암호(보안키)가 올바르지 않습니다.")
    return {"message": "암호가 설정되었습니다."}
