# -*- encoding: utf-8 -*-
"""
用户认证路由

提供注册、登录、密码修改等功能。
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.lib.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.lib.database import db_manager
from backend.lib.database.models import UserModel

router = APIRouter(prefix="/api/auth", tags=["用户认证"])

# ============================================================================
# 请求/响应模型
# ============================================================================


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: EmailStr


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class AuthResponse(BaseModel):
    """认证响应"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


# ============================================================================
# 路由定义
# ============================================================================


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> Dict[str, Any]:
    """
    用户注册
    
    - **username**: 用户名（必填，唯一）
    - **password**: 密码（必填，至少 6 位）
    - **email**: 邮箱（必填，唯一）
    """
    # 验证密码长度
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为 6 位"
        )
    
    with db_manager.get_cursor() as cursor:
        # 检查用户名是否存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否存在
        cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        
        # 创建用户
        password_hash = get_password_hash(request.password)
        sql, params = UserModel.insert_sql(request.username, password_hash, request.email)
        cursor.execute(sql, params)
        user_id = cursor.lastrowid
        
        # 获取用户信息
        cursor.execute(
            "SELECT id, username, email, role, status, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> Dict[str, Any]:
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    """
    with db_manager.get_cursor() as cursor:
        # 查询用户
        cursor.execute(
            """
            SELECT id, username, email, role, status, password_hash, last_login, created_at
            FROM users
            WHERE username = %s
            """,
            (request.username,)
        )
        user = cursor.fetchone()
        
        # 验证用户
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        if not verify_password(request.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 检查用户状态
        if user['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )
        
        # 更新最后登录时间
        sql, params = UserModel.update_last_login_sql(user['id'])
        cursor.execute(sql, params)
        
        # 移除敏感字段
        user_data = {k: v for k, v in user.items() if k != 'password_hash'}
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取当前用户信息
    
    需要携带有效的 JWT 令牌。
    """
    return current_user


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """
    修改密码
    
    - **old_password**: 原密码
    - **new_password**: 新密码（至少 6 位）
    """
    # 验证新密码长度
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度至少为 6 位"
        )
    
    with db_manager.get_cursor() as cursor:
        # 查询用户密码
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = %s",
            (current_user['id'],)
        )
        user = cursor.fetchone()
        
        # 验证原密码
        if not verify_password(request.old_password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原密码错误"
            )
        
        # 更新密码
        new_hash = get_password_hash(request.new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_hash, current_user['id'])
        )
        db_manager.get_connection().commit()
    
    return {"status": "success", "message": "密码已修改"}
