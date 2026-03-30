# -*- encoding: utf-8 -*-
"""
用户认证模块

提供 JWT 令牌生成、验证、密码加密等功能。
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.lib.database import db_manager
from backend.lib.database.models import UserModel

# ============================================================================
# 配置
# ============================================================================

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production-please-use-env-var"  # 生产环境请从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

# OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# ============================================================================
# 密码管理
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        密码哈希
    """
    return pwd_context.hash(password)

# ============================================================================
# JWT 令牌管理
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT 令牌
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码访问令牌
    
    Args:
        token: JWT 令牌
        
    Returns:
        解码后的数据，失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ============================================================================
# 用户认证
# ============================================================================


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    获取当前用户
    
    Args:
        token: JWT 令牌
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # 从数据库查询用户
    with db_manager.get_cursor() as cursor:
        cursor.execute(
            "SELECT id, username, email, role, status, avatar, created_at FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
    
    if not user:
        raise credentials_exception
    
    # 检查用户状态
    if user['status'] != 'active':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 用户未激活
    """
    if current_user['status'] != 'active':
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    获取当前管理员用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        管理员用户信息
        
    Raises:
        HTTPException: 非管理员
    """
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
