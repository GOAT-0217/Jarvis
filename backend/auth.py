import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")  # JWT密钥
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # JWT算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 过期时间
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "")  # 管理员邀请码
PBKDF2_ROUNDS = int(os.getenv("PASSWORD_PBKDF2_ROUNDS", "310000"))  # 密码哈希轮数

# 定义OAuth2密码 bearer 认证方案 同时 指定登录接口： /auth/login，用于后续身份验证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    """
    数据库会话依赖项。
        它创建SessionLocal实例，
        通过yield提供db供路由使用，确保请求结束后在finally块中关闭连接，
        防止资源泄漏，常用于FastAPI等框架的依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """该函数验证密码"""
    # 1. 检查输入非空
    if not plain_password or not password_hash:
        return False

    # New format: pbkdf2_sha256$<rounds>$<salt_b64>$<digest_b64>
    # 2. 若为PBKDF2格式，手动解码盐值和哈希，计算并安全比对；
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            calculated = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt,
                int(rounds),
            )
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False
    # 3. 若为Bcrypt旧格式，使用passlib库验证
    # Backward compatibility for legacy passlib/bcrypt hashes.
    if password_hash.startswith("$2") or password_hash.startswith("$bcrypt"):
        try:
            from passlib.context import CryptContext

            legacy_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
            return legacy_context.verify(plain_password, password_hash)
        except Exception:
            return False
    # 4. 其他情况或异常均返回False，确保兼容性与安全性。
    return False


def get_password_hash(password: str) -> str:
    """该函数用于生成密码哈希。"""
    if not password:
        raise ValueError("password is required")
    # 校验密码非空，接着生成随机盐值，使用PBKDF2-HMAC-SHA256算法结合盐值和指定迭代次数计算摘要。
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ROUNDS,
    )
    # 将盐值和摘要进行Base64编码，并按特定格式拼接返回字符串，确保密码安全存储
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt_b64}${digest_b64}"


def create_access_token(username: str, role: str) -> str:
    """该函数用于生成JWT访问令牌。"""
    # 计算过期时间
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 构建包含用户名、角色和过期时间的payload
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    # 使用密钥和指定算法编码并返回JWT字符串。
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """该函数用于用户认证:
        1.首先根据用户名查询数据库，若用户不存在则返回None；
        2.接着调用verify_password比对输入密码与哈希值，验证失败返回None；
        3.两者均通过则返回用户对象，实现安全的登录校验逻辑
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """该函数用于获取当前认证用户"""
    # 它解析JWT令牌提取用户名，若令牌无效或缺失则抛出401异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的认证令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # 在数据库中查询对应用户，若用户不存在也抛出异常，否则返回用户对象，实现身份验证与用户检索。
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """该函数用于验证用户是否为管理员:确保只有管理员能继续执行后续操作"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员权限不足")
    return current_user


def resolve_role(requested_role: str | None, admin_code: str | None) -> str:
    """该函数用于解析用户角色:
        若请求角色非“admin”，直接返回“user”；
        若为“admin”，则校验邀请码，匹配成功返回“admin”，否则抛出403错误。
        默认情况下，空值或无效角色均视为普通用户
    """
    role = (requested_role or "user").strip().lower()
    if role != "admin":
        return "user"
    if ADMIN_INVITE_CODE and admin_code == ADMIN_INVITE_CODE:
        return "admin"
    raise HTTPException(status_code=403, detail="管理员邀请码错误")
