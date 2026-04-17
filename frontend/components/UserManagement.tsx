import React, { useState, useEffect } from 'react';
import { User } from '../types';
import api from '../services/api';
import { toast } from './Toast';

interface UserManagementProps {
  onClose?: () => void;
}

export const UserManagement: React.FC<UserManagementProps> = ({ onClose }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    role: 'user' as 'user' | 'admin',
    status: 'active' as 'active' | 'inactive' | 'banned',
    password: '',
  });
  const [editPosition, setEditPosition] = useState({ x: 0, y: 0 });

  // 获取用户列表
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await api.users.list();
      setUsers(data);
    } catch (error: any) {
      toast.error(`获取用户列表失败: ${error.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 处理编辑用户
  const handleEditUser = (user: User, event: React.MouseEvent) => {
    setEditingUser(user);
    setFormData({
      email: user.email || '',
      role: user.role,
      status: user.status,
      password: '',
    });
    
    // 计算编辑框位置
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    setEditPosition({
      x: rect.left,
      y: rect.top + rect.height + 10
    });
  };

  // 处理取消编辑
  const handleCancelEdit = () => {
    setEditingUser(null);
  };

  // 处理删除用户
  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`确定要删除用户 ${username} 吗？`)) {
      return;
    }

    try {
      await api.users.delete(userId);
      toast.success('用户删除成功');
      fetchUsers();
    } catch (error: any) {
      toast.error(`删除用户失败: ${error.detail || error.message}`);
    }
  };

  // 处理表单提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;

    try {
      console.log('开始更新用户信息:', editingUser.id, formData);
      const response = await api.users.update(editingUser.id, formData);
      console.log('更新用户信息成功:', response);
      toast.success('用户信息更新成功');
      setEditingUser(null);
      fetchUsers();
    } catch (error: any) {
      console.error('更新用户信息失败:', error);
      toast.error(`更新用户信息失败: ${error.detail || error.message}`);
    }
  };

  // 处理表单输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="h-full w-full p-6 relative overflow-auto">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">用户管理</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors"
            aria-label="关闭"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        )}
      </div>

      {/* 统计信息卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 w-full">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex flex-col justify-between h-32">
          <div className="text-sm font-medium text-gray-500">总用户数</div>
          <div className="text-3xl font-bold text-gray-900 mt-2">{users.length}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex flex-col justify-between h-32">
          <div className="text-sm font-medium text-gray-500">管理员</div>
          <div className="text-3xl font-bold text-blue-600 mt-2">{users.filter(u => u.role === 'admin').length}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex flex-col justify-between h-32">
          <div className="text-sm font-medium text-gray-500">活跃用户</div>
          <div className="text-3xl font-bold text-green-600 mt-2">{users.filter(u => u.status === 'active').length}</div>
        </div>
      </div>

      {/* 加载状态 */}
      {loading ? (
        <div className="flex items-center justify-center py-24 w-full">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden w-full">
          <div className="overflow-x-auto">
            <table className="w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    用户名
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    邮箱
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    角色
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    创建时间
                  </th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.username}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      <div className="truncate max-w-[300px]">{user.email || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.role === 'admin' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {user.role === 'admin' ? '管理员' : '普通用户'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.status === 'active' 
                          ? 'bg-green-100 text-green-800' 
                          : user.status === 'inactive' 
                          ? 'bg-yellow-100 text-yellow-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.status === 'active' ? '活跃' : user.status === 'inactive' ? '未激活' : '禁用'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.created_at ? new Date(user.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-3">
                        <button
                          onClick={(e) => handleEditUser(user, e)}
                          className="text-blue-600 hover:text-blue-800 px-3 py-1.5 rounded text-xs transition-colors"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.id, user.username)}
                          className="text-red-600 hover:text-red-800 px-3 py-1.5 rounded text-xs transition-colors"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {users.length === 0 && (
            <div className="py-16 text-center text-gray-500">
              暂无用户数据
            </div>
          )}
        </div>
      )}

      {/* 悬浮编辑框 */}
      {editingUser && (
        <div 
          className="fixed z-50 bg-white rounded-lg shadow-xl p-5 w-96 border border-gray-200"
          style={{
            left: `${Math.max(0, editPosition.x)}px`,
            top: `${Math.max(0, editPosition.y)}px`,
            transform: 'translateX(-50%)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">编辑用户</h3>
            <button
              onClick={handleCancelEdit}
              className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              aria-label="关闭"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  用户名
                </label>
                <input
                  type="text"
                  value={editingUser.username}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  邮箱
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  角色
                </label>
                <select
                  name="role"
                  value={formData.role}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                >
                  <option value="user">普通用户</option>
                  <option value="admin">管理员</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  状态
                </label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                >
                  <option value="active">活跃</option>
                  <option value="inactive">未激活</option>
                  <option value="banned">禁用</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  密码（留空不修改）
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="输入新密码"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-2">
              <button
                type="button"
                onClick={handleCancelEdit}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors text-sm"
              >
                取消
              </button>
              <button
                type="submit"
                className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
              >
                保存
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
