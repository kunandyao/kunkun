import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Trash2, CheckCircle, XCircle, Server } from 'lucide-react';
import api from '../services/api';

interface DatabaseStatus {
  connected: boolean;
  statistics?: {
    hot_search_count: number;
    video_count: number;
    comment_count: number;
    scheduler_count: number;
  };
}

interface DatabaseStatistics {
  total: {
    hot_search: number;
    videos: number;
    comments: number;
    scheduler_runs: number;
  };
  latest_comments: any[];
  top_comments: any[];
}

const DatabaseManager: React.FC = () => {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [statistics, setStatistics] = useState<DatabaseStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // 获取数据库状态
  const fetchStatus = async () => {
    try {
      const result = await api.hotComment.database.getStatus();
      if (result.success) {
        setStatus(result.data);
      }
    } catch (error) {
      console.error('获取数据库状态失败:', error);
    }
  };

  // 获取统计信息
  const fetchStatistics = async () => {
    try {
      const result = await api.hotComment.database.getStatistics();
      if (result.success) {
        setStatistics(result.data);
      }
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  // 初始化数据库
  const handleInitDatabase = async () => {
    if (!confirm('确定要初始化数据库吗？这将创建所有必要的表。')) {
      return;
    }

    setInitializing(true);
    try {
      const result = await api.hotComment.database.init();
      if (result.success) {
        setMessage({ type: 'success', text: '数据库初始化成功！' });
        fetchStatus();
        fetchStatistics();
      } else {
        setMessage({ type: 'error', text: '数据库初始化失败' });
      }
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || '初始化失败，请检查 MySQL 配置' 
      });
    } finally {
      setInitializing(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  // 清空数据
  const handleClearData = async (table?: string) => {
    const tableName = table || '所有表';
    if (!confirm(`确定要清空 ${tableName} 吗？此操作不可恢复！`)) {
      return;
    }

    setLoading(true);
    try {
      const result = await api.hotComment.database.clear(table);
      if (result.success) {
        setMessage({ type: 'success', text: `已清空 ${tableName}` });
        fetchStatus();
        fetchStatistics();
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: `清空失败：${error.response?.data?.detail}` });
    } finally {
      setLoading(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  // 刷新数据
  const handleRefresh = () => {
    fetchStatus();
    fetchStatistics();
  };

  useEffect(() => {
    fetchStatus();
    fetchStatistics();
  }, []);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Database className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-bold text-gray-900">MySQL 数据库管理</h2>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center space-x-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          <span>刷新</span>
        </button>
      </div>

      {/* 消息提示 */}
      {message && (
        <div className={`mb-4 p-3 rounded ${
          message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {message.text}
        </div>
      )}

      {/* 数据库连接状态 */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">连接状态</h3>
        <div className="flex items-center space-x-2">
          {status?.connected ? (
            <>
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-green-600 font-medium">已连接</span>
            </>
          ) : (
            <>
              <XCircle className="w-5 h-5 text-red-600" />
              <span className="text-red-600 font-medium">未连接</span>
            </>
          )}
        </div>
      </div>

      {/* 数据统计 */}
      {statistics && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">数据统计</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">热榜数据</div>
              <div className="text-2xl font-bold text-blue-600">
                {statistics.total.hot_search.toLocaleString()}
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">视频数据</div>
              <div className="text-2xl font-bold text-green-600">
                {statistics.total.videos.toLocaleString()}
              </div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">评论数据</div>
              <div className="text-2xl font-bold text-purple-600">
                {statistics.total.comments.toLocaleString()}
              </div>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">任务执行</div>
              <div className="text-2xl font-bold text-orange-600">
                {statistics.total.scheduler_runs.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-700">管理操作</h3>
        
        {!status?.connected && (
          <button
            onClick={handleInitDatabase}
            disabled={initializing}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
          >
            <Server className="w-5 h-5" />
            <span>{initializing ? '初始化中...' : '初始化数据库'}</span>
          </button>
        )}

        {status?.connected && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button
              onClick={() => handleClearData('comments')}
              disabled={loading}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-red-50 hover:bg-red-100 disabled:bg-gray-100 text-red-600 rounded-lg font-medium transition-colors"
            >
              <Trash2 className="w-5 h-5" />
              <span>清空评论数据</span>
            </button>
            <button
              onClick={() => handleClearData('videos')}
              disabled={loading}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-red-50 hover:bg-red-100 disabled:bg-gray-100 text-red-600 rounded-lg font-medium transition-colors"
            >
              <Trash2 className="w-5 h-5" />
              <span>清空视频数据</span>
            </button>
            <button
              onClick={() => handleClearData('hot_search')}
              disabled={loading}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-red-50 hover:bg-red-100 disabled:bg-gray-100 text-red-600 rounded-lg font-medium transition-colors"
            >
              <Trash2 className="w-5 h-5" />
              <span>清空热榜数据</span>
            </button>
            <button
              onClick={() => handleClearData()}
              disabled={loading}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
            >
              <Trash2 className="w-5 h-5" />
              <span>清空所有数据</span>
            </button>
          </div>
        )}
      </div>

      {/* 配置说明 */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">配置说明</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• 首次使用需要先初始化数据库</li>
          <li>• 确保 MySQL 服务已启动</li>
          <li>• 默认数据库名：douyin_hot_comments</li>
          <li>• 默认端口：3306</li>
          <li>• 修改配置请编辑：backend/lib/database/config.py</li>
        </ul>
      </div>
    </div>
  );
};

export default DatabaseManager;
