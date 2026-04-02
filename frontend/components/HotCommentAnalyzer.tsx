import { Download, Clock, Users, MessageSquare, Play, Square, RefreshCw, ExternalLink } from 'lucide-react';
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { TaskType } from '../types';

interface HotVideo {
  title: string;
  hot_value: string;
  rank: number;
  url: string;
  mobile_url: string;
  aweme_id?: string;
  comments_count?: number;
  success?: boolean;
  error?: string;
}

interface CrawlResult {
  success: boolean;
  videos: HotVideo[];
  total_comments: number;
  error?: string;
}

interface HotCommentAnalyzerProps {
  setActiveTab: (tab: TaskType) => void;
  autoCrawlVideoId?: string;
  autoCrawlTitle?: string;
}

export const HotCommentAnalyzer: React.FC<HotCommentAnalyzerProps> = ({ setActiveTab, autoCrawlVideoId, autoCrawlTitle }) => {
  const [crawling, setCrawling] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [crawlResult, setCrawlResult] = useState<CrawlResult | null>(null);
  const [crawlMode, setCrawlMode] = useState<'range' | 'count'>('count');
  const [startRank, setStartRank] = useState(1);
  const [endRank, setEndRank] = useState(10);
  const [videoCount, setVideoCount] = useState(10);
  const [commentsPerVideo, setCommentsPerVideo] = useState(100);
  const [saveToDb, setSaveToDb] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [schedulerRunning, setSchedulerRunning] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);
  const [intervalHours, setIntervalHours] = useState(2);

  useEffect(() => {
    // 加载定时任务状态
    loadSchedulerStatus();
    const timer = setInterval(loadSchedulerStatus, 5000);
    
    // 加载爬取状态
    loadCrawlStatus();
    
    // 定期检查爬取状态（处理页面跳转回来的情况）
    const crawlTimer = setInterval(loadCrawlStatus, 3000);
    
    return () => {
      clearInterval(timer);
      clearInterval(crawlTimer);
    };
  }, []);

  // 加载爬取状态
  const loadCrawlStatus = async () => {
    try {
      const result = await api.hotComment.getCrawlStatus();
      if (result.success && result.data) {
        setCrawling(result.data.crawling);
        if (result.data.crawl_result) {
          setCrawlResult(result.data.crawl_result.data);
        }
      }
    } catch (err) {
      console.error('加载爬取状态失败:', err);
    }
  };

  // 只在组件首次加载时检查是否需要自动爬取，跳转回来时不自动刷新
  const [hasAutoCrawled, setHasAutoCrawled] = useState(false);
  
  useEffect(() => {
    if (autoCrawlVideoId && !crawling && !crawlResult && !hasAutoCrawled) {
      setHasAutoCrawled(true);
      handleCrawlSingleVideo(autoCrawlVideoId, autoCrawlTitle);
    }
  }, [autoCrawlVideoId, autoCrawlTitle]);

  const handleCrawlSingleVideo = async (videoId: string, title?: string) => {
    setCrawling(true);
    setError(null);
    try {
      // 构建视频 ID 到标题的映射
      const videoTitles: Record<string, string> = {};
      if (title) {
        videoTitles[videoId] = title;
      }
      
      const result = await api.hotComment.crawl({
        video_count: 1,
        comments_per_video: commentsPerVideo,
        save_to_csv: true,
        save_to_db: saveToDb,
        video_ids: [videoId],
        video_titles: videoTitles,  // 传递标题映射
      });
      
      if (result.success) {
        setCrawlResult(result.data);
        if (title) {
          result.data.videos.forEach((v: any) => {
            if (!v.title) v.title = title;
          });
        }
      } else {
        setError(result.message || '爬取失败');
      }
    } catch (err: any) {
      setError(err.message || '爬取失败，请检查网络连接和 Cookie 配置');
      console.error('Crawl error:', err);
    } finally {
      setCrawling(false);
    }
  };

  const loadSchedulerStatus = async () => {
    try {
      const result = await api.hotComment.getSchedulerStatus();
      if (result.success) {
        setSchedulerStatus(result.data);
        setSchedulerRunning(result.data.is_running);
        setIntervalHours(result.data.interval_hours || 2);
      }
    } catch (err) {
      console.error('加载定时任务状态失败:', err);
    }
  };

  const handleCrawl = async () => {
    setCrawling(true);
    setError(null);
    try {
      // 根据模式计算视频数量
      const actualVideoCount = crawlMode === 'range' ? (endRank - startRank + 1) : videoCount;
      
      const result = await api.hotComment.crawl({
        video_count: actualVideoCount,
        comments_per_video: commentsPerVideo,
        save_to_csv: true,
        save_to_db: saveToDb,
        start_rank: crawlMode === 'range' ? startRank : undefined,
        end_rank: crawlMode === 'range' ? endRank : undefined,
      });
      
      if (result.success) {
        setCrawlResult(result.data);
      } else {
        setError(result.message || '爬取失败');
      }
    } catch (err: any) {
      setError(err.message || '爬取失败，请检查网络连接和 Cookie 配置');
      console.error('Crawl error:', err);
    } finally {
      setCrawling(false);
    }
  };

  const handleStartScheduler = async () => {
    try {
      const result = await api.hotComment.startScheduler({
        interval_hours: intervalHours,
        video_count: videoCount,
        comments_per_video: commentsPerVideo,
        save_to_db: saveToDb,
      });
      
      if (result.success) {
        setSchedulerRunning(true);
        setSchedulerStatus(result.data);
      }
    } catch (err: any) {
      console.error('启动定时任务失败:', err);
    }
  };

  const handleStopScheduler = async () => {
    try {
      const result = await api.hotComment.stopScheduler();
      if (result.success) {
        setSchedulerRunning(false);
      }
    } catch (err: any) {
      console.error('停止定时任务失败:', err);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.hotComment.analyze({
        generate_report: false
      });
      if (result.success) {
        alert('数据分析完成！');
      } else {
        setError(result.message || '分析失败');
      }
    } catch (err: any) {
      setError(err.message || '分析失败');
      console.error('Analyze error:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGoToDashboard = () => {
    setActiveTab(TaskType.HOT_COMMENT_DASHBOARD);
  };

  return (
    <div className="h-screen w-full bg-[#F5F6F7] overflow-auto">
      <div className="max-w-[1600px] mx-auto p-6">
        <div className="flex items-center justify-between mb-6 bg-white rounded-lg p-4 shadow-sm border border-[#DEE0E3]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#3370FF] to-[#0066FF] rounded-lg flex items-center justify-center">
              <MessageSquare size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-[#1D2129] mb-0.5">热榜评论采集</h1>
              <p className="text-sm text-[#86909C]">爬取抖音热榜视频评论并进行数据预处理</p>
            </div>
          </div>
          <button
            onClick={() => setActiveTab(TaskType.HOT_COMMENT_DASHBOARD)}
            className="px-4 py-2 bg-[#3370FF] text-white rounded-md text-sm font-medium hover:bg-[#2860E1] transition-all flex items-center gap-2"
          >
            <ExternalLink size={18} />
            查看数据大屏
          </button>
        </div>

        <div className="bg-white rounded-lg border border-[#DEE0E3] p-6 mb-4">
          <h2 className="text-base font-semibold text-[#1D2129] mb-4">爬取配置</h2>
          
          {/* 爬取模式选择 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-[#4E5969] mb-2">
              爬取模式
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={crawlMode === 'count'}
                  onChange={() => setCrawlMode('count')}
                  className="w-4 h-4 text-[#3370FF] border-[#C9CDD4] focus:ring-[#3370FF]"
                />
                <span className="text-sm text-[#4E5969]">前 N 名热榜</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={crawlMode === 'range'}
                  onChange={() => setCrawlMode('range')}
                  className="w-4 h-4 text-[#3370FF] border-[#C9CDD4] focus:ring-[#3370FF]"
                />
                <span className="text-sm text-[#4E5969]">指定排名范围</span>
              </label>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            {crawlMode === 'count' ? (
              <div>
                <label className="block text-sm font-medium text-[#4E5969] mb-2">
                  爬取视频数量
                </label>
                <input
                  type="number"
                  value={videoCount}
                  onChange={(e) => setVideoCount(parseInt(e.target.value) || 10)}
                  min="1"
                  max="30"
                  className="w-full px-3 py-2 bg-white border border-[#C9CDD4] rounded-md text-sm text-[#1D2129] focus:ring-2 focus:ring-[#3370FF] focus:border-transparent"
                />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-[#4E5969] mb-2">
                    起始排名
                  </label>
                  <input
                    type="number"
                    value={startRank}
                    onChange={(e) => setStartRank(parseInt(e.target.value) || 1)}
                    min="1"
                    max="30"
                    className="w-full px-3 py-2 bg-white border border-[#C9CDD4] rounded-md text-sm text-[#1D2129] focus:ring-2 focus:ring-[#3370FF] focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#4E5969] mb-2">
                    结束排名
                  </label>
                  <input
                    type="number"
                    value={endRank}
                    onChange={(e) => setEndRank(parseInt(e.target.value) || 10)}
                    min="1"
                    max="30"
                    className="w-full px-3 py-2 bg-white border border-[#C9CDD4] rounded-md text-sm text-[#1D2129] focus:ring-2 focus:ring-[#3370FF] focus:border-transparent"
                  />
                </div>
                <div className="flex items-end">
                  <div className="text-sm text-[#86909C] pb-2">
                    将爬取第 {startRank} 到第 {endRank} 名，共 {endRank - startRank + 1} 个视频
                  </div>
                </div>
              </>
            )}
            
            <div>
              <label className="block text-sm font-medium text-[#4E5969] mb-2">
                每个视频评论数
              </label>
              <input
                type="number"
                value={commentsPerVideo}
                onChange={(e) => setCommentsPerVideo(parseInt(e.target.value) || 100)}
                min="10"
                max="1000"
                className="w-full px-3 py-2 bg-white border border-[#C9CDD4] rounded-md text-sm text-[#1D2129] focus:ring-2 focus:ring-[#3370FF] focus:border-transparent"
              />
            </div>
            
            <div className="flex items-end">
              <button
                onClick={handleCrawl}
                disabled={crawling}
                className="w-full px-4 py-2 bg-[#3370FF] text-white rounded-md text-sm font-medium hover:bg-[#2860E1] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Download size={18} className={crawling ? 'animate-spin' : ''} />
                {crawling ? '爬取中...' : '开始爬取'}
              </button>
            </div>
          </div>

          <div className="mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={saveToDb}
                onChange={(e) => setSaveToDb(e.target.checked)}
                className="w-4 h-4 rounded border-[#C9CDD4] text-[#3370FF] focus:ring-[#3370FF]"
              />
              <span className="text-sm text-[#4E5969]">
                保存到 MySQL 数据库（勾选后将评论写入数据库）
              </span>
            </label>
          </div>

          <div className="border-t border-[#EDEEF0] pt-4 mt-4">
            <h3 className="text-base font-semibold text-[#1D2129] mb-4 flex items-center gap-2">
              <Clock size={18} className="text-[#3370FF]" />
              定时自动爬取
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-[#4E5969] mb-2">
                  爬取间隔（小时）
                </label>
                <select
                  value={intervalHours}
                  onChange={(e) => setIntervalHours(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-[#C9CDD4] rounded-md text-sm text-[#1D2129] focus:ring-2 focus:ring-[#3370FF] focus:border-transparent"
                >
                  <option value="1">1 小时</option>
                  <option value="2">2 小时</option>
                  <option value="4">4 小时</option>
                  <option value="6">6 小时</option>
                  <option value="12">12 小时</option>
                  <option value="24">24 小时</option>
                </select>
              </div>
              
              <div className="md:col-span-3 flex items-end gap-4">
                {!schedulerRunning ? (
                  <button
                    onClick={handleStartScheduler}
                    className="flex-1 px-4 py-2 bg-[#00B42A] text-white rounded-md text-sm font-medium hover:bg-[#009A29] transition-all flex items-center justify-center gap-2"
                  >
                    <Play size={18} />
                    启动定时任务
                  </button>
                ) : (
                  <button
                    onClick={handleStopScheduler}
                    className="flex-1 px-4 py-2 bg-[#F53F3F] text-white rounded-md text-sm font-medium hover:bg-[#D92828] transition-all flex items-center justify-center gap-2"
                  >
                    <Square size={18} />
                    停止定时任务
                  </button>
                )}
              </div>
            </div>

            {schedulerStatus && (
              <div className={`rounded-lg p-4 ${
                schedulerRunning 
                  ? 'bg-[#E8F8F0] border border-[#00B42A]/30' 
                  : 'bg-[#F7F8FA] border border-[#C9CDD4]'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  {schedulerRunning ? (
                    <>
                      <RefreshCw size={18} className="text-[#00B42A] animate-spin" />
                      <span className="text-sm font-medium text-[#00B42A]">定时任务运行中</span>
                    </>
                  ) : (
                    <>
                      <Clock size={18} className="text-[#86909C]" />
                      <span className="text-sm font-medium text-[#86909C]">定时任务未运行</span>
                    </>
                  )}
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-[#86909C]">间隔时间:</span>
                    <span className="text-[#1D2129] ml-2">{schedulerStatus.interval_hours || 0} 小时</span>
                  </div>
                  <div>
                    <span className="text-[#86909C]">视频数量:</span>
                    <span className="text-[#1D2129] ml-2">{schedulerStatus.video_count || 0}</span>
                  </div>
                  <div>
                    <span className="text-[#86909C]">评论数/视频:</span>
                    <span className="text-[#1D2129] ml-2">{schedulerStatus.comments_per_video || 0}</span>
                  </div>
                  <div>
                    <span className="text-[#86909C]">总运行次数:</span>
                    <span className="text-[#1D2129] ml-2">{schedulerStatus.total_runs || 0}</span>
                  </div>
                  {schedulerStatus.last_run_time && (
                    <div>
                      <span className="text-[#86909C]">上次运行:</span>
                      <span className="text-[#1D2129] ml-2">
                        {new Date(schedulerStatus.last_run_time).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  )}
                  {schedulerStatus.next_run_time && (
                    <div>
                      <span className="text-[#86909C]">下次运行:</span>
                      <span className="text-[#1D2129] ml-2">
                        {new Date(schedulerStatus.next_run_time).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  )}
                  {schedulerStatus.total_comments > 0 && (
                    <div>
                      <span className="text-[#86909C]">总评论数:</span>
                      <span className="text-[#1D2129] ml-2">{schedulerStatus.total_comments}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {crawlResult && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-green-700 mb-2">
                <Users size={20} />
                <span className="font-medium">爬取成功</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">视频数量:</span>
                  <span className="text-gray-900 ml-2 font-medium">{crawlResult.videos.length}</span>
                </div>
                <div>
                  <span className="text-gray-600">评论总数:</span>
                  <span className="text-gray-900 ml-2 font-medium">{crawlResult.total_comments}</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-red-400">
                <MessageSquare size={20} />
                <span>{error}</span>
              </div>
            </div>
          )}

          {crawlResult && (
            <div className="space-y-4">
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="w-full px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg shadow-purple-500/30 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <MessageSquare size={18} className={analyzing ? 'animate-spin' : ''} />
                {analyzing ? '分析中...' : '数据分析'}
              </button>
              <button
                onClick={handleGoToDashboard}
                className="w-full px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg shadow-purple-500/30 flex items-center justify-center gap-2"
              >
                <ExternalLink size={18} />
                查看数据大屏
              </button>
            </div>
          )}
        </div>

        <div className="bg-gradient-to-r from-[#3370FF] to-[#006BFF] rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <ExternalLink size={18} className="text-white/90" />
            下一步
          </h2>
          <p className="text-white/90 text-sm leading-relaxed">
            爬取完成后，点击"查看数据大屏"按钮，系统会自动完成数据清洗、分析，并在大屏上展示结果。
          </p>
        </div>

        {!crawlResult && !crawling && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <MessageSquare size={64} className="text-gray-500 mx-auto mb-4" />
              <p className="text-gray-400 text-lg mb-4">配置爬取参数后开始采集热榜评论</p>
              <p className="text-gray-500 text-sm">支持定时任务、数据库存储、Spark 数据预处理</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
