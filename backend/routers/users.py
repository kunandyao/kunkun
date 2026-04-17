# -*- encoding: utf-8 -*-
"""
用户管理路由

提供用户列表、用户详情、权限调整等功能。
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.lib.auth import get_current_admin_user, get_password_hash
from backend.lib.database import db_manager

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# ============================================================================
# 请求/响应模型
# ============================================================================


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    email: str = None
    role: str = None
    status: str = None
    password: str = None


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str = None
    role: str
    status: str
    last_login: str = None
    created_at: str


# ============================================================================
# 路由定义
# ============================================================================


@router.get("", response_model=List[UserResponse])
async def get_users(
    current_user: dict = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """
    获取用户列表
    
    仅管理员可访问，返回系统中的所有用户信息。
    """
    with db_manager.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role, status, last_login, created_at
            FROM users
            ORDER BY created_at DESC
            """
        )
        users = cursor.fetchall()
    
    # 转换datetime对象为字符串
    for user in users:
        if user.get('last_login'):
            user['last_login'] = str(user['last_login'])
        if user.get('created_at'):
            user['created_at'] = str(user['created_at'])
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    获取用户详情
    
    仅管理员可访问，根据用户ID返回用户详细信息。
    
    - **user_id**: 用户ID
    """
    with db_manager.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role, status, last_login, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 转换datetime对象为字符串
    if user.get('last_login'):
        user['last_login'] = str(user['last_login'])
    if user.get('created_at'):
        user['created_at'] = str(user['created_at'])
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    更新用户信息
    
    仅管理员可访问，用于更新用户的邮箱、角色、状态和密码。
    
    - **user_id**: 用户ID
    - **email**: 邮箱（可选）
    - **role**: 角色（可选，值为 'user' 或 'admin'）
    - **status**: 状态（可选，值为 'active', 'inactive' 或 'banned'）
    - **password**: 密码（可选，至少6位）
    """
    # 验证角色和状态值
    if request.role and request.role not in ['user', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色必须是 'user' 或 'admin'"
        )
    
    if request.status and request.status not in ['active', 'inactive', 'banned']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="状态必须是 'active', 'inactive' 或 'banned'"
        )
    
    if request.password and len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为6位"
        )
    
    with db_manager.get_cursor() as cursor:
        # 检查用户是否存在
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 构建更新语句
        update_fields = []
        update_params = []
        
        if request.email:
            # 检查邮箱是否已被其他用户使用
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND id != %s",
                (request.email, user_id)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被使用"
                )
            update_fields.append("email = %s")
            update_params.append(request.email)
        
        if request.role:
            update_fields.append("role = %s")
            update_params.append(request.role)
        
        if request.status:
            update_fields.append("status = %s")
            update_params.append(request.status)
        
        if request.password:
            password_hash = get_password_hash(request.password)
            update_fields.append("password_hash = %s")
            update_params.append(password_hash)
        
        if update_fields:
            update_sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            update_params.append(user_id)
            cursor.execute(update_sql, update_params)
            db_manager.get_connection().commit()
        
        # 获取更新后的用户信息
        cursor.execute(
            """
            SELECT id, username, email, role, status, last_login, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 转换datetime对象为字符串
    if user.get('last_login'):
        user['last_login'] = str(user['last_login'])
    if user.get('created_at'):
        user['created_at'] = str(user['created_at'])
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    删除用户
    
    仅管理员可访问，用于删除指定的用户。
    
    - **user_id**: 用户ID
    """
    # 不允许删除当前登录的管理员
    if user_id == current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账户"
        )
    
    with db_manager.get_cursor() as cursor:
        # 检查用户是否存在
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 删除用户
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db_manager.get_connection().commit()
    
    return {"status": "success", "message": "用户已删除"}
