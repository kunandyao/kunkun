import { X, RefreshCw, ExternalLink } from 'lucide-react';
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface HotItem {
  title: string;
  ranks: number[];
  url: string;
  mobileUrl: string;
  hotValue: string;
}

interface HotSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HotSearchModal: React.FC<HotSearchModalProps> = ({ isOpen, onClose }) => {
  const [hotData, setHotData] = useState<Record<string, HotItem>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchHotData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.hot.douyin();
      setHotData(data);
      setLastUpdated(new Date().toLocaleString());
    } catch (err) {
      setError('获取热榜数据失败，请重试');
      console.error('Error fetching hot data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHotData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const hotItems = Object.entries(hotData).map(([title, data], index) => {
    const linkUrl = data.mobileUrl || data.url;
    const rank = index + 1;
    const isTop = rank <= 3;

    return (
      <div 
        key={title} 
        className={`p-3 rounded-lg mb-2 flex gap-3 items-start ${isTop ? 'bg-red-50 border border-red-100' : 'bg-gray-50 border border-gray-100'}`}
      >
        <div className={`text-lg font-bold min-w-[24px] text-center ${isTop ? 'text-red-600' : 'text-gray-600'}`}>
          {rank}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 line-clamp-2 mb-1">
            {linkUrl ? (
              <a 
                href={linkUrl} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="hover:text-blue-600 flex items-center gap-1"
              >
                {title}
                <ExternalLink size={12} className="inline" />
              </a>
            ) : (
              title
            )}
          </p>
          {data.hotValue && (
            <div className="text-xs text-gray-500">
              热度：{data.hotValue}
            </div>
          )}
        </div>
      </div>
    );
  });

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">抖音热榜</h2>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                更新于：{lastUpdated}
              </span>
            )}
            <button
              onClick={fetchHotData}
              disabled={loading}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
              title="刷新热榜"
            >
              <RefreshCw size={18} className={`text-gray-600 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
              title="关闭"
            >
              <X size={18} className="text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <button
                  onClick={fetchHotData}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  重试
                </button>
              </div>
            </div>
          ) : hotItems.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-gray-500">暂无热榜数据</p>
            </div>
          ) : (
            <div className="space-y-2">
              {hotItems}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 flex justify-between items-center">
          <div className="text-xs text-gray-500">
            数据来源：抖音热榜
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};