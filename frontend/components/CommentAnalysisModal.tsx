import React, { useState, useEffect } from 'react';
import { X, BarChart3, MessageSquare, Users, ThumbsUp, MapPin, Clock, Smile, Loader2, FileText, Image as ImageIcon, ExternalLink } from 'lucide-react';
import { bridge } from '../services/bridge';
import { logger } from '../services/logger';
import { toast } from './Toast';

interface CommentAnalysisModalProps {
  csvFile?: string;
  onClose: () => void;
}

interface AnalysisResult {
  total: number;
  hot_words?: Array<[string, number]>;
  location_distribution?: Array<[string, number]>;
  time_distribution?: {
    by_hour?: Array<[number, number]>;
    by_date?: Array<[string, number]>;
  };
  sentiment?: {
    positive: number;
    negative: number;
    neutral: number;
    positive_rate: number;
    negative_rate: number;
    neutral_rate: number;
  };
  top_comments?: Array<{
    id: string;
    nickname: string;
    text: string;
    digg_count: number;
  }>;
  user_activity?: {
    total_users: number;
    avg_comments_per_user: number;
    top_users: Array<[string, number]>;
  };
}

export const CommentAnalysisModal: React.FC<CommentAnalysisModalProps> = ({
  csvFile,
  onClose,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [htmlReport, setHtmlReport] = useState<string | null>(null);
  const [wordcloud, setWordcloud] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'hotwords' | 'location' | 'time' | 'sentiment'>('overview');

  useEffect(() => {
    performAnalysis();
  }, [csvFile]);

  const performAnalysis = async () => {
    setIsLoading(true);
    try {
      const result = await bridge.analyzeComments(csvFile, true);
      setAnalysis(result.analysis as unknown as AnalysisResult);
      setHtmlReport(result.html_report || null);
      setWordcloud(result.wordcloud || null);
      toast.success('评论分析完成');
    } catch (e) {
      const msg = e instanceof Error ? e.message : '分析失败';
      toast.error(msg);
      logger.error('[CommentAnalysis] 分析失败:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const openReport = async () => {
    if (htmlReport) {
      try {
        // 尝试用系统默认浏览器打开
        const reportUrl = bridge.getMediaUrl(htmlReport);
        bridge.openExternal(reportUrl);
      } catch {
        toast.error('无法打开报告');
      }
    }
  };

  const openWordcloud = async () => {
    if (wordcloud) {
      try {
        const imageUrl = bridge.getMediaUrl(wordcloud);
        bridge.openExternal(imageUrl);
      } catch {
        toast.error('无法打开词云图');
      }
    }
  };

  const renderOverview = () => {
    if (!analysis) return null;

    return (
      <div className="space-y-4">
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-blue-600 mb-1">
              <MessageSquare size={18} />
              <span className="text-sm font-medium">总评论数</span>
            </div>
            <div className="text-2xl font-bold text-blue-700">{analysis.total?.toLocaleString() || 0}</div>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-green-600 mb-1">
              <Users size={18} />
              <span className="text-sm font-medium">独立用户</span>
            </div>
            <div className="text-2xl font-bold text-green-700">
              {analysis.user_activity?.total_users?.toLocaleString() || 0}
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-purple-600 mb-1">
              <Smile size={18} />
              <span className="text-sm font-medium">正面评价</span>
            </div>
            <div className="text-2xl font-bold text-purple-700">
              {analysis.sentiment?.positive_rate || 0}%
            </div>
          </div>

          <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-orange-600 mb-1">
              <ThumbsUp size={18} />
              <span className="text-sm font-medium">人均评论</span>
            </div>
            <div className="text-2xl font-bold text-orange-700">
              {analysis.user_activity?.avg_comments_per_user || 0}
            </div>
          </div>
        </div>

        {/* 热门评论 */}
        {analysis.top_comments && analysis.top_comments.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <ThumbsUp size={16} className="text-red-500" />
              热门评论 TOP5
            </h3>
            <div className="space-y-2">
              {analysis.top_comments.slice(0, 5).map((comment, idx) => (
                <div key={comment.id} className="flex items-start gap-3 p-2 bg-gray-50 rounded-lg">
                  <span className="flex-shrink-0 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {idx + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-800 truncate">{comment.nickname}</div>
                    <div className="text-xs text-gray-600 line-clamp-2">{comment.text}</div>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-red-500">
                    <ThumbsUp size={12} />
                    {comment.digg_count}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 报告按钮 */}
        {(htmlReport || wordcloud) && (
          <div className="flex gap-2">
            {htmlReport && (
              <button
                onClick={openReport}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors"
              >
                <FileText size={16} />
                查看完整报告
                <ExternalLink size={14} />
              </button>
            )}
            {wordcloud && (
              <button
                onClick={openWordcloud}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-purple-50 text-purple-600 rounded-lg text-sm font-medium hover:bg-purple-100 transition-colors"
              >
                <ImageIcon size={16} />
                查看词云图
                <ExternalLink size={14} />
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderHotWords = () => {
    if (!analysis?.hot_words || analysis.hot_words.length === 0) {
      return <div className="text-center text-gray-500 py-8">暂无热门词汇数据</div>;
    }

    return (
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {analysis.hot_words.slice(0, 30).map(([word, count], idx) => {
            const size = Math.max(12, 24 - idx * 0.5);
            const opacity = Math.max(0.5, 1 - idx * 0.02);
            return (
              <span
                key={word}
                className="inline-flex items-center gap-1 px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-full cursor-default transition-transform hover:scale-105"
                style={{ fontSize: `${size}px`, opacity }}
              >
                {word}
                <span className="text-xs opacity-80">({count})</span>
              </span>
            );
          })}
        </div>

        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">详细列表</h4>
          <div className="grid grid-cols-2 gap-2">
            {analysis.hot_words.slice(0, 20).map(([word, count], idx) => (
              <div key={word} className="flex items-center justify-between p-2 bg-white rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 bg-gray-100 text-gray-600 text-xs rounded flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-sm text-gray-800">{word}</span>
                </div>
                <span className="text-xs text-gray-500">{count}次</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderLocation = () => {
    if (!analysis?.location_distribution || analysis.location_distribution.length === 0) {
      return <div className="text-center text-gray-500 py-8">暂无地区分布数据</div>;
    }

    const total = analysis.location_distribution.reduce((sum, [, count]) => sum + count, 0);

    return (
      <div className="space-y-3">
        {analysis.location_distribution.slice(0, 15).map(([location, count], idx) => {
          const percentage = ((count / total) * 100).toFixed(1);
          return (
            <div key={location} className="flex items-center gap-3">
              <span className="w-6 text-sm text-gray-500">{idx + 1}</span>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-800 flex items-center gap-1">
                    <MapPin size={14} className="text-blue-500" />
                    {location}
                  </span>
                  <span className="text-xs text-gray-500">{count} ({percentage}%)</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderTime = () => {
    if (!analysis?.time_distribution?.by_hour || analysis.time_distribution.by_hour.length === 0) {
      return <div className="text-center text-gray-500 py-8">暂无时间分布数据</div>;
    }

    const { by_hour } = analysis.time_distribution;
    const maxCount = Math.max(...by_hour.map(([, count]) => count));

    return (
      <div className="space-y-4">
        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Clock size={16} />
            24小时分布
          </h4>
          <div className="flex items-end gap-1 h-32">
            {by_hour.map(([hour, count]) => {
              const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
              return (
                <div key={hour} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t transition-all duration-500"
                    style={{ height: `${height}%` }}
                    title={`${hour}时: ${count}条`}
                  />
                  <span className="text-xs text-gray-500">{hour}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 活跃时段统计 */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '凌晨 (0-6)', hours: [0, 1, 2, 3, 4, 5], color: 'bg-indigo-100 text-indigo-700' },
            { label: '白天 (6-18)', hours: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17], color: 'bg-yellow-100 text-yellow-700' },
            { label: '晚上 (18-24)', hours: [18, 19, 20, 21, 22, 23], color: 'bg-purple-100 text-purple-700' },
          ].map(({ label, hours, color }) => {
            const count = by_hour
              .filter(([h]) => hours.includes(h))
              .reduce((sum, [, c]) => sum + c, 0);
            return (
              <div key={label} className={`p-3 rounded-xl ${color}`}>
                <div className="text-xs opacity-80">{label}</div>
                <div className="text-lg font-bold">{count}条</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderSentiment = () => {
    if (!analysis?.sentiment) {
      return <div className="text-center text-gray-500 py-8">暂无情感分析数据</div>;
    }

    const { positive, negative, neutral, positive_rate, negative_rate, neutral_rate } = analysis.sentiment;
    const total = positive + negative + neutral;

    return (
      <div className="space-y-4">
        {/* 情感分布饼图 */}
        <div className="flex items-center justify-center py-4">
          <div className="relative w-40 h-40">
            <svg viewBox="0 0 100 100" className="transform -rotate-90">
              {total > 0 && (
                <>
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="20"
                    strokeDasharray={`${(positive / total) * 251.2} 251.2`}
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="20"
                    strokeDasharray={`${(neutral / total) * 251.2} 251.2`}
                    strokeDashoffset={`${-(positive / total) * 251.2}`}
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="20"
                    strokeDasharray={`${(negative / total) * 251.2} 251.2`}
                    strokeDashoffset={`${-((positive + neutral) / total) * 251.2}`}
                  />
                </>
              )}
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-800">{total}</div>
                <div className="text-xs text-gray-500">总评论</div>
              </div>
            </div>
          </div>
        </div>

        {/* 图例 */}
        <div className="space-y-2">
          {[
            { label: '正面', count: positive, rate: positive_rate, color: 'bg-green-500' },
            { label: '中性', count: neutral, rate: neutral_rate, color: 'bg-yellow-500' },
            { label: '负面', count: negative, rate: negative_rate, color: 'bg-red-500' },
          ].map(({ label, count, rate, color }) => (
            <div key={label} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${color}`} />
                <span className="text-sm font-medium text-gray-700">{label}</span>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-gray-800">{count}条</div>
                <div className="text-xs text-gray-500">{rate}%</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-[600px] max-h-[85vh] flex flex-col animate-in zoom-in-95 duration-200 border border-gray-200/50"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 flex items-center justify-between border-b border-gray-100 bg-gray-50/30">
          <div className="flex items-center gap-2">
            <BarChart3 size={20} className="text-blue-500" />
            <span className="font-bold text-gray-800">评论数据分析</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-800 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100">
          {[
            { id: 'overview', label: '概览', icon: BarChart3 },
            { id: 'hotwords', label: '热词', icon: MessageSquare },
            { id: 'location', label: '地区', icon: MapPin },
            { id: 'time', label: '时间', icon: Clock },
            { id: 'sentiment', label: '情感', icon: Smile },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'text-blue-600 border-b-2 border-blue-500 bg-blue-50/50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="animate-spin text-blue-500 mb-3" size={32} />
              <p className="text-gray-500">正在分析评论数据...</p>
            </div>
          ) : (
            <>
              {activeTab === 'overview' && renderOverview()}
              {activeTab === 'hotwords' && renderHotWords()}
              {activeTab === 'location' && renderLocation()}
              {activeTab === 'time' && renderTime()}
              {activeTab === 'sentiment' && renderSentiment()}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-100 bg-gray-50/30 flex justify-between items-center">
          <button
            onClick={performAnalysis}
            disabled={isAnalyzing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors disabled:opacity-50"
          >
            {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <BarChart3 size={14} />}
            重新分析
          </button>
          <span className="text-xs text-gray-400">
            基于 {analysis?.total || 0} 条评论
          </span>
        </div>
      </div>
    </div>
  );
};
