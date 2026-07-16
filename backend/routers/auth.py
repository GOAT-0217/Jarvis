"""Auth routes — register, login, current-user."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
    resolve_role,
    verify_password,
)
from models import User
from schemas import APIResponse, AuthResponse, ChangePasswordRequest, CurrentUserResponse, LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse[AuthResponse])
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = (request.username or "").strip()
    password = (request.password or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")

    role = resolve_role(request.role, request.admin_code)
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
        nickname=(request.nickname or "").strip() or None,
        email=(request.email or "").strip() or None,
    )
    db.add(user)
    db.commit()

    token = create_access_token(username=username, role=role)
    return APIResponse(data=AuthResponse(access_token=token, username=username, role=role))


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(username=user.username, role=user.role)
    return APIResponse(data=AuthResponse(access_token=token, username=user.username, role=user.role))


@router.get("/me", response_model=APIResponse[CurrentUserResponse])
async def me(current_user: User = Depends(get_current_user)):
    return APIResponse(data=CurrentUserResponse(
        username=current_user.username,
        role=current_user.role,
        nickname=current_user.nickname,
        email=current_user.email,
    ))


@router.put("/password", response_model=APIResponse[dict])
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.new_password or not request.new_password.strip():
        raise HTTPException(status_code=400, detail="新密码不能为空")

    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="旧密码错误")

    current_user.password_hash = get_password_hash(request.new_password.strip())
    db.commit()

    return APIResponse(data={"message": "密码已修改"})
