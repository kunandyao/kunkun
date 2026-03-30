import { RefreshCw, Flame, TrendingUp, Clock, MessageSquare } from 'lucide-react';
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { TaskType } from '../types';

interface HotItem {
  id?: number;
  title: string;
  ranks: number[];
  url: string;
  mobileUrl: string;
  hotValue: string;
  rank?: number;
  video_id?: string;
  crawl_time?: string;
}

interface DatabaseHotItem {
  id: number;
  rank: number;
  title: string;
  hot_value: string;
  video_id: string | null;
  crawl_time: string | null;
  url: string;
  mobileUrl: string;
}

interface HotSearchDashboardProps {
  setActiveTab: (tab: TaskType) => void;
  onAnalyzeHotItem?: (videoId: string, title: string) => void;
}

export const HotSearchDashboard: React.FC<HotSearchDashboardProps> = ({ setActiveTab, onAnalyzeHotItem }) => {
  const [hotData, setHotData] = useState<Record<string, HotItem>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [useDatabase, setUseDatabase] = useState(true);  // 默认从数据库读取
  const [dbStatus, setDbStatus] = useState<{isStale?: boolean; timeAgo?: string}>({});
  const [previousHotData, setPreviousHotData] = useState<Record<string, HotItem>>({});  // 保存上一次的数据

  const handleAnalyzeHotItem = (item: HotItem) => {
    if (item.video_id && onAnalyzeHotItem) {
      onAnalyzeHotItem(item.video_id, item.title);
      setActiveTab(TaskType.HOT_COMMENT);
    } else if (item.video_id) {
      setActiveTab(TaskType.HOT_COMMENT);
    } else {
      alert('该热榜暂无关联视频，无法分析评论');
    }
  };

  // 从数据库获取热榜数据
  const fetchFromDatabase = async () => {
    try {
      const result = await api.hot.douyinFromDb(30);
      if (result.success && result.data) {
        // 转换数据格式
        const convertedData: Record<string, HotItem> = {};
        result.data.forEach((item: DatabaseHotItem) => {
          convertedData[item.title] = {
            id: item.id,
            title: item.title,
            ranks: [item.rank],
            url: item.url,
            mobileUrl: item.mobileUrl,
            hotValue: item.hot_value,
            rank: item.rank,
            video_id: item.video_id || undefined,
            crawl_time: item.crawl_time || undefined,
          };
        });
        setPreviousHotData(hotData);  // 保存旧数据
        setHotData(convertedData);
        setLastUpdated(result.latest_time ? new Date(result.latest_time).toLocaleString() : new Date().toLocaleString());
        setDbStatus({
          isStale: result.is_stale,
          timeAgo: result.time_ago,
        });
        return true;
      }
      return false;
    } catch (err) {
      console.error('从数据库获取热榜失败:', err);
      return false;
    }
  };

  // 从 API 获取热榜数据
  const fetchFromAPI = async () => {
    const apiData = await api.hot.douyin();
    // 转换 API 返回的数据为 HotItem 类型
    const convertedData: Record<string, HotItem> = {};
    Object.entries(apiData).forEach(([title, item]) => {
      convertedData[title] = {
        title,
        ranks: item.ranks,
        url: item.url,
        mobileUrl: item.mobileUrl,
        hotValue: item.hotValue,
      };
    });
    setPreviousHotData(hotData);  // 保存旧数据
    setHotData(convertedData);
    setLastUpdated(new Date().toLocaleString());
  };

  const fetchHotData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (useDatabase) {
        const success = await fetchFromDatabase();
        if (!success) {
          // 数据库没有数据，切换到 API
          setUseDatabase(false);
          await fetchFromAPI();
        }
      } else {
        await fetchFromAPI();
      }
    } catch (err) {
      setError('获取热榜数据失败，请重试');
      console.error('Error fetching hot data:', err);
    } finally {
      setLoading(false);
    }
  };

  // 刷新到数据库
  const refreshToDatabase = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.hot.douyinRefreshDb();
      if (result.success) {
        setUseDatabase(true);
        await fetchFromDatabase();
      } else {
        setError(result.message || '刷新失败');
      }
    } catch (err: any) {
      setError(err.message || '刷新失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHotData();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchHotData, 60000); // 每分钟刷新一次
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const hotItems = Object.entries(hotData).map(([title, data], index) => {
    const linkUrl = data.mobileUrl || data.url;
    const rank = index + 1;
    const isTop = rank <= 3;

    return {
      rank,
      title,
      linkUrl,
      hotValue: data.hotValue,
      isTop,
    };
  });

  const top3Items = hotItems.slice(0, 3);
  const otherItems = hotItems.slice(3);

  return (
    <div className="h-screen w-full bg-[#F5F6F7] p-6 overflow-auto">
      <div className="max-w-[1600px] mx-auto w-full">
        <div className="flex items-center justify-between mb-6 bg-white rounded-lg p-4 shadow-sm border border-[#DEE0E3]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#3370FF] to-[#0066FF] rounded-lg flex items-center justify-center">
              <Flame size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-[#1D2129] mb-0.5">抖音热榜</h1>
              <div className="flex items-center gap-2 text-[#86909C]">
                <Clock size={14} />
                <span className="text-xs">
                  {lastUpdated ? `更新于 ${lastUpdated}` : '加载中...'}
                  {dbStatus.timeAgo && ` (${dbStatus.timeAgo})`}
                </span>
                {dbStatus.isStale && (
                  <span className="text-[#FF7D00] ml-2">数据可能已过期</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refreshToDatabase}
              disabled={loading}
              className="px-4 py-2 bg-[#3370FF] text-white rounded-md text-sm font-medium hover:bg-[#2860E1] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
              title="刷新热榜数据并保存到数据库"
            >
              <TrendingUp size={16} />
              刷新到数据库
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
                autoRefresh
                  ? 'bg-[#00B42A] text-white'
                  : 'bg-white text-[#4E5969] border border-[#DEE0E3] hover:bg-[#F7F8FA]'
              }`}
            >
              {autoRefresh ? '自动刷新：开启' : '自动刷新：关闭'}
            </button>
            <button
              onClick={fetchHotData}
              disabled={loading}
              className="px-4 py-2 bg-white text-[#3370FF] border border-[#3370FF] rounded-md text-sm font-medium hover:bg-[#F2F3F5] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              刷新
            </button>
          </div>
        </div>

        {loading && hotItems.length === 0 ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <RefreshCw size={40} className="text-[#3370FF] animate-spin mx-auto mb-3" />
              <p className="text-[#86909C] text-sm">加载热榜数据中...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="w-14 h-14 bg-[#F53F3F]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <Flame size={28} className="text-[#F53F3F]" />
              </div>
              <p className="text-[#F53F3F] text-sm mb-3">{error}</p>
              <button
                onClick={fetchHotData}
                className="px-4 py-2 bg-[#3370FF] text-white rounded-md text-sm font-medium hover:bg-[#2860E1] transition-all"
              >
                重试
              </button>
            </div>
          </div>
        ) : hotItems.length === 0 ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <Flame size={40} className="text-[#C9CDD4] mx-auto mb-3" />
              <p className="text-[#86909C] text-sm">暂无热榜数据</p>
            </div>
          </div>
        ) : (
          <>
            {/* 加载时的骨架屏 */}
            {loading && (
              <div className="fixed inset-0 bg-[#000000]/10 backdrop-blur-[2px] z-50 flex items-center justify-center">
                <div className="bg-white rounded-lg p-6 shadow-lg border border-[#DEE0E3]">
                  <RefreshCw size={32} className="text-[#3370FF] animate-spin mx-auto mb-3" />
                  <p className="text-[#1D2129] text-sm">刷新中...</p>
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              {top3Items.map((item) => {
                const originalItem = Object.values(hotData)[item.rank - 1];
                return (
                  <div
                    key={item.title}
                    className="bg-white rounded-lg p-4 border border-[#DEE0E3] hover:shadow-md transition-all group"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-8 h-8 rounded-md flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                          item.rank === 1
                            ? 'bg-[#F53F3F] text-white'
                            : item.rank === 2
                            ? 'bg-[#FF7D00] text-white'
                            : item.rank === 3
                            ? 'bg-[#00B42A] text-white'
                            : 'bg-[#F2F3F5] text-[#4E5969]'
                        }`}
                      >
                        {item.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-[#1D2129] line-clamp-2 mb-2">
                          {item.title}
                        </h3>
                        <div className="flex items-center justify-between">
                          {item.hotValue && (
                            <div className="flex items-center gap-1 text-[#86909C]">
                              <TrendingUp size={12} />
                              <span className="text-xs">{item.hotValue}</span>
                            </div>
                          )}
                          <button
                            onClick={() => originalItem && handleAnalyzeHotItem(originalItem)}
                            disabled={!originalItem?.video_id}
                            className={`p-2 rounded-md transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
                              originalItem?.video_id
                                ? 'bg-[#3370FF] hover:bg-[#2860E1]'
                                : 'bg-[#F2F3F5]'
                            }`}
                            title={originalItem?.video_id ? '爬取评论分析' : '暂无视频'}
                          >
                            <MessageSquare size={16} className={originalItem?.video_id ? 'text-white' : 'text-[#C9CDD4]'} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="bg-white rounded-lg border border-[#DEE0E3] overflow-hidden">
              <div className="bg-[#F7F8FA] px-4 py-3 border-b border-[#DEE0E3]">
                <h2 className="text-sm font-semibold text-[#1D2129] flex items-center gap-2">
                  <TrendingUp size={16} className="text-[#3370FF]" />
                  热门榜单
                </h2>
              </div>
              <div className="divide-y divide-[#EDEEF0]">
                {otherItems.map((item) => {
                  const originalItem = Object.values(hotData)[item.rank - 1];
                  return (
                    <div
                      key={item.title}
                      className="px-4 py-3 hover:bg-[#F7F8FA] transition-all group"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-7 h-7 rounded-md flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                            item.rank <= 3
                              ? 'bg-gradient-to-br from-[#F53F3F] to-[#FF7D00] text-white'
                              : 'bg-[#F2F3F5] text-[#4E5969]'
                          }`}
                        >
                          {item.rank}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-[#1D2129] line-clamp-1 mb-1">
                            {item.title}
                          </h3>
                          {item.hotValue && (
                            <div className="flex items-center gap-1 text-[#86909C] text-xs">
                              <TrendingUp size={11} />
                              <span>{item.hotValue}</span>
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => originalItem && handleAnalyzeHotItem(originalItem)}
                          disabled={!originalItem?.video_id}
                          className={`p-2 rounded-md transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
                            originalItem?.video_id
                              ? 'bg-[#3370FF] hover:bg-[#2860E1]'
                              : 'bg-[#F2F3F5]'
                          }`}
                          title={originalItem?.video_id ? '爬取评论分析' : '暂无视频'}
                        >
                          <MessageSquare size={16} className={originalItem?.video_id ? 'text-white' : 'text-[#C9CDD4]'} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-8 text-center text-gray-500 text-sm">
              <p>数据来源：抖音热榜 | 共 {hotItems.length} 条热点</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
