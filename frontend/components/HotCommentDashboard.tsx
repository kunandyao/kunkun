import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../services/api';

interface RealVideoAnalysis {
  file: string;
  filepath: string;
  title?: string;
  cover_url?: string;  // 封面图 URL
  aweme_id: string;
  analysis: {
    total: number;
    hot_words: Array<[string, number]>;
    location_distribution: Array<[string, number]>;
    sentiment: {
      positive: number;
      negative: number;
      neutral: number;
      positive_rate: number;
      negative_rate: number;
      neutral_rate: number;
    };
    top_comments: Array<{
      nickname: string;
      text: string;
      digg_count: number;
      create_time: string;
      ip_label?: string;
    }>;
    time_distribution: {
      by_hour: Array<[number, number]>;
      by_date: Array<[string, number]>;
    };
    user_activity: {
      total_users: number;
      avg_comments_per_user: number;
      top_users: Array<[string, number]>;
    };
  };
  report: any;
  total_comments: number;
}

interface RealAnalyzeResponse {
  video_analyses: RealVideoAnalysis[];
  total_videos: number;
  total_all_comments: number;
}

const getSentimentFromAnalysis = (analysis: RealVideoAnalysis['analysis']): 'positive' | 'neutral' | 'negative' | 'controversial' => {
  const { sentiment } = analysis;
  const posRate = sentiment.positive_rate;
  const negRate = sentiment.negative_rate;
  
  if (posRate > 60) return 'positive';
  if (negRate > 40) return 'negative';
  if (Math.abs(posRate - negRate) < 20) return 'controversial';
  return 'neutral';
};

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive':
      return 'from-green-500 to-emerald-600';
    case 'negative':
      return 'from-red-500 to-rose-600';
    case 'controversial':
      return 'from-orange-500 to-amber-600';
    default:
      return 'from-gray-500 to-slate-600';
  }
};

const getSentimentLabel = (sentiment: string) => {
  switch (sentiment) {
    case 'positive':
      return '正面';
    case 'negative':
      return '负面';
    case 'controversial':
      return '争议';
    default:
      return '中性';
  }
};

const getSentimentBadgeColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive':
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'negative':
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'controversial':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }
};

interface HotCommentDashboardProps {
  refreshTrigger?: number;
}

export const HotCommentDashboard: React.FC<HotCommentDashboardProps> = ({ refreshTrigger }) => {
  const [videoAnalyses, setVideoAnalyses] = useState<RealVideoAnalysis[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hotHistoryData, setHotHistoryData] = useState<{ times: string[]; series: any[] } | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadAnalyses();
    loadHotHistory();
  }, [refreshTrigger]);

  const loadHotHistory = async () => {
    try {
      const result = await api.hot.douyinHistory(10);
      if (result.success && result.times && result.series) {
        setHotHistoryData({
          times: result.times,
          series: result.series
        });
      }
    } catch (err) {
      console.error('加载热榜历史数据失败:', err);
    }
  };

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 首先尝试从数据库获取数据
      let result = await api.hotComment.getAnalysisFromDb();
      console.log('API返回数据:', result);
      if (result.success && result.data && result.data.video_analyses && result.data.video_analyses.length > 0) {
        console.log('总视频数:', result.data.video_analyses.length);
        console.log('第一条数据:', result.data.video_analyses[0]);
        // 只保留有封面的视频
        const analysesWithCover = result.data.video_analyses.filter((v: any) => v.cover_url);
        console.log('有封面的视频数:', analysesWithCover.length);
        setVideoAnalyses(analysesWithCover);
        setSelectedIndex(0);
        return;
      }
      
      // 如果数据库没有数据，则尝试分析现有文件
      console.log('数据库中没有分析数据，尝试分析现有文件...');
      result = await api.hotComment.analyze();
      if (result.success && result.data) {
        // 只保留有封面的视频
        const analysesWithCover = (result.data.video_analyses || []).filter((v: any) => v.cover_url);
        setVideoAnalyses(analysesWithCover);
        if (analysesWithCover.length > 0) {
          setSelectedIndex(0);
        }
      }
    } catch (err) {
      console.error('加载分析数据失败:', err);
      setError('加载分析数据失败，请先爬取热榜评论');
    } finally {
      setLoading(false);
    }
  };

  const selectedAnalysis = videoAnalyses[selectedIndex];
  const sentiment = selectedAnalysis ? getSentimentFromAnalysis(selectedAnalysis.analysis) : 'neutral';

  const sentimentPieChartOption = selectedAnalysis ? {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { top: '5%', left: 'center', textStyle: { color: '#fff' } },
    series: [
      {
        name: '情感分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '60%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#1e293b',
          borderWidth: 2,
        },
        label: { show: true, color: '#fff' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' },
        },
        data: [
          { value: selectedAnalysis.analysis.sentiment.positive, name: '正面', itemStyle: { color: '#10b981' } },
          { value: selectedAnalysis.analysis.sentiment.neutral, name: '中性', itemStyle: { color: '#6b7280' } },
          { value: selectedAnalysis.analysis.sentiment.negative, name: '负面', itemStyle: { color: '#ef4444' } },
        ],
      },
    ],
  } : {};

  const hotWordsBarChartOption = selectedAnalysis ? {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: selectedAnalysis.analysis.hot_words.slice(0, 10).map(([word]) => word),
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    series: [
      {
        name: '频次',
        type: 'bar',
        barWidth: '60%',
        data: selectedAnalysis.analysis.hot_words.slice(0, 10).map(([, count]) => count),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#8b5cf6' },
              { offset: 1, color: '#7c3aed' },
            ],
          },
        },
      },
    ],
  } : {};

  const ipBarChartOption = selectedAnalysis ? {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: selectedAnalysis.analysis.location_distribution.slice(0, 10).map(([location]) => location),
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    series: [
      {
        name: '人数',
        type: 'bar',
        barWidth: '60%',
        data: selectedAnalysis.analysis.location_distribution.slice(0, 10).map(([, count]) => count),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#06b6d4' },
              { offset: 1, color: '#0891b2' },
            ],
          },
        },
      },
    ],
  } : {};

  const timeLineChartOption = selectedAnalysis ? {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: selectedAnalysis.analysis.time_distribution.by_hour.map(([hour]) => `${hour}时`),
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    series: [
      {
        name: '评论数',
        type: 'line',
        smooth: true,
        data: selectedAnalysis.analysis.time_distribution.by_hour.map(([, count]) => count),
        itemStyle: { color: '#f59e0b' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245, 158, 11, 0.5)' },
              { offset: 1, color: 'rgba(245, 158, 11, 0.1)' },
            ],
          },
        },
      },
    ],
  } : {};

  const hotTrendChartOption = hotHistoryData ? {
    // 背景渐变色
    backgroundColor: {
      type: 'linear',
      x: 0,
      y: 0,
      x2: 0,
      y2: 1,
      colorStops: [
        { offset: 0, color: '#1a103a' },
        { offset: 1, color: '#2d1b5a' }
      ]
    },
    // 图例
    legend: {
      right: 20,
      top: 'center',
      orient: 'vertical',
      textStyle: { color: '#ffffff' }
    },
    // 网格
    grid: { left: '10%', right: '20%', bottom: '10%', top: '10%', containLabel: true },
    // 工具提示
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function(params: any) {
        let result = params[0].name + '<br/>';
        params.forEach((param: any) => {
          result += `${param.marker} ${param.seriesName}: ${param.value}M<br/>`;
        });
        return result;
      }
    },
    // X轴
    xAxis: {
      type: 'category',
      data: hotHistoryData.times.map(time => {
        const date = new Date(time);
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
      }),
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: { color: '#ffffff' },
      splitLine: { show: false }
    },
    // Y轴
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: {
        color: '#ffffff',
        formatter: '{value}M'
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#333',
          type: 'dashed'
        }
      },
      min: 0
    },
    // 系列数据 - 将数据转换为百万单位
    series: hotHistoryData.series.map((s, idx) => {
      const colors = [
        '#9370DB', '#FF69B4', '#FFA500', '#3CB371', '#4169E1',
        '#9370DB', '#FF69B4', '#FFA500', '#3CB371', '#4169E1'
      ];
      return {
        name: s.name,
        type: 'line',
        smooth: true,
        data: s.data.map((val: number) => Number((val / 1000000).toFixed(1))),
        lineStyle: {
          width: 2,
          color: colors[idx % colors.length],
          opacity: 0.85
        },
        itemStyle: {
          color: colors[idx % colors.length],
          borderColor: '#ffffff',
          borderWidth: 1
        },
        symbol: 'circle',
        symbolSize: 8
      };
    }),
  } : {};

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white items-center justify-center">
        <div className="text-xl">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white items-center justify-center">
        <div className="text-xl text-red-400 mb-4">{error}</div>
        <button
          onClick={loadAnalyses}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          重新加载
        </button>
      </div>
    );
  }

  if (videoAnalyses.length === 0) {
    return (
      <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white items-center justify-center">
        <div className="text-xl mb-4">暂无分析数据</div>
        <p className="text-slate-400 mb-4">请先在"热榜评论分析"页面爬取热榜评论</p>
        <button
          onClick={loadAnalyses}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          刷新数据
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white overflow-hidden">
      {/* Header */}
      <div className="bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50 px-6 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              热榜评论舆情大屏
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              共分析 {videoAnalyses.length} 个视频，{videoAnalyses.reduce((sum, v) => sum + v.total_comments, 0)} 条评论
            </p>
          </div>
          <button
            onClick={loadAnalyses}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2 text-sm"
          >
            🔄 刷新数据
          </button>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Top Video List */}
        <div className="bg-slate-800/50 border-b border-slate-700/50 px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-purple-500 rounded"></span>
              热榜视频列表
            </h2>
          </div>
          <div
            ref={scrollContainerRef}
            className="flex gap-3 overflow-x-auto pb-3"
            style={{ scrollbarWidth: 'thin', scrollbarColor: '#475569 #1e293b' }}
          >
            {videoAnalyses.map((videoAnalysis, index) => {
              const videoSentiment = getSentimentFromAnalysis(videoAnalysis.analysis);
              return (
                <div
                  key={videoAnalysis.aweme_id}
                  onClick={() => setSelectedIndex(index)}
                  className={`flex-shrink-0 w-32 cursor-pointer transition-all duration-200 ${
                    selectedIndex === index
                      ? 'scale-105 ring-2 ring-blue-500/50'
                      : 'hover:scale-103 opacity-80 hover:opacity-100'
                  }`}
                >
                  <div className="bg-slate-800/80 backdrop-blur-sm rounded-xl overflow-hidden border border-slate-700/50 shadow-lg hover:shadow-xl hover:border-slate-600/50 transition-all">
                    {/* 封面区域 - 统一高度 */}
                    <div className="relative h-36 bg-slate-900">
                      <div
                        className={`absolute top-2 left-2 w-6 h-6 rounded-full bg-gradient-to-br ${getSentimentColor(
                          videoSentiment
                        )} flex items-center justify-center font-bold text-xs shadow-md z-10`}
                      >
                        {index + 1}
                      </div>
                      {videoAnalysis.cover_url ? (
                        <img
                          src={`http://127.0.0.1:8000/api/hot-comment/proxy-cover?url=${encodeURIComponent(videoAnalysis.cover_url)}`}
                          alt="封面"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      ) : null}
                      {/* 默认图标或错误占位 */}
                      <div className={`absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-slate-700 to-slate-800 ${videoAnalysis.cover_url ? 'hidden' : ''}`}>
                        <span className="text-2xl mb-1">🎬</span>
                        <span className="text-[10px] text-slate-400">无封面</span>
                      </div>
                      {/* 选中状态 */}
                      {selectedIndex === index && (
                        <div className="absolute inset-0 bg-blue-500/15 flex items-center justify-center">
                          <div className="w-8 h-8 rounded-full bg-blue-500/80 flex items-center justify-center">
                            <div className="w-2.5 h-2.5 bg-white rounded-full"></div>
                          </div>
                        </div>
                      )}
                    </div>
                    {/* 信息区域 */}
                    <div className="p-2 bg-slate-800/50">
                      <p className="text-xs text-white line-clamp-2 leading-tight min-h-[2.5rem]">{videoAnalysis.title || videoAnalysis.file}</p>
                      <div className="flex items-center justify-between mt-1.5">
                        <span className="text-[10px] text-slate-400">{videoAnalysis.total_comments} 评论</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getSentimentBadgeColor(
                            videoSentiment
                          )}`}
                        >
                          {getSentimentLabel(videoSentiment)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Analysis Dashboard */}
        <div className="px-6 py-4">
          <div className="max-w-7xl mx-auto">
          {/* Hot Trend Chart */}
          {hotHistoryData && hotHistoryData.times.length > 1 && (
            <div className="mb-6">
              <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
                <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-gradient-to-r from-red-500 to-orange-500 rounded-full"></span>
                  热榜热度趋势 TOP 10
                </h3>
                <div className="h-72">
                  <ReactECharts option={hotTrendChartOption} style={{ height: '100%' }} />
                </div>
              </div>
            </div>
          )}

          {/* Video Title */}
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white mb-1">{selectedAnalysis.title || selectedAnalysis.file}</h2>
            <p className="text-slate-400 text-sm">视频 ID: {selectedAnalysis.aweme_id}</p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 backdrop-blur-lg border border-blue-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-400 text-xs font-medium mb-1">评论总数</p>
                  <p className="text-2xl font-bold text-white">{selectedAnalysis.analysis.total}</p>
                </div>
                <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-xl">💬</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-500/20 to-green-600/20 backdrop-blur-lg border border-green-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-400 text-xs font-medium mb-1">正面评价</p>
                  <p className="text-2xl font-bold text-white">{selectedAnalysis.analysis.sentiment.positive_rate}%</p>
                </div>
                <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-xl">😊</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 backdrop-blur-lg border border-purple-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-400 text-xs font-medium mb-1">舆情结论</p>
                  <p
                    className={`text-xl font-bold ${
                      sentiment === 'positive'
                        ? 'text-green-400'
                        : sentiment === 'negative'
                        ? 'text-red-400'
                        : sentiment === 'controversial'
                        ? 'text-orange-400'
                        : 'text-gray-400'
                    }`}
                  >
                    {getSentimentLabel(sentiment)}
                  </p>
                </div>
                <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-xl">📊</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 backdrop-blur-lg border border-orange-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-orange-400 text-xs font-medium mb-1">独立用户</p>
                  <p className="text-2xl font-bold text-white">{selectedAnalysis.analysis.user_activity.total_users}</p>
                </div>
                <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-xl">👥</span>
                </div>
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                情感分布
              </h3>
              <div className="h-64">
                <ReactECharts option={sentimentPieChartOption} style={{ height: '100%' }} />
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                热门词汇 TOP 10
              </h3>
              <div className="h-64">
                <ReactECharts option={hotWordsBarChartOption} style={{ height: '100%' }} />
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                IP 地区分布 TOP 10
              </h3>
              <div className="h-64">
                <ReactECharts option={ipBarChartOption} style={{ height: '100%' }} />
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                评论时间分布（按小时）
              </h3>
              <div className="h-64">
                <ReactECharts option={timeLineChartOption} style={{ height: '100%' }} />
              </div>
            </div>
          </div>

          {/* Top Comments */}
          {selectedAnalysis.analysis.top_comments.length > 0 && (
            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4 mb-4">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-rose-500 rounded-full"></span>
                热门评论 TOP 5
              </h3>
              <div className="space-y-3">
                {selectedAnalysis.analysis.top_comments.slice(0, 5).map((comment, idx) => (
                  <div key={idx} className="bg-slate-700/30 rounded-lg p-3">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{comment.nickname}</span>
                        {comment.ip_label && (
                          <span className="text-xs text-gray-400 bg-slate-600 px-2 py-0.5 rounded">
                            {comment.ip_label}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                          👍 {comment.digg_count}
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-300 text-sm">{comment.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          </div>
        </div>
      </div>
    </div>
  );
};
