import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { Download, FileText } from 'lucide-react';
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
      model: string;
    };
    topics: {
      num_topics: number;
      topics: Array<{
        topic_id: number;
        keywords: string;
        top_words: Array<string>;
      }>;
      model: string;
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
    console.log('useEffect 运行，refreshTrigger:', refreshTrigger);
    loadAnalyses();
    loadHotHistory();
  }, [refreshTrigger]);

  const loadHotHistory = async () => {
    try {
      console.log('开始加载热榜历史数据...');
      const result = await api.hot.douyinHistory(10);
      console.log('热榜历史数据返回:', result);
      if (result && result.success && result.times && result.series) {
        console.log('热榜历史数据成功:', { times: result.times, series: result.series });
        console.log('times长度:', result.times.length);
        console.log('series长度:', result.series.length);
        setHotHistoryData({
          times: result.times,
          series: result.series
        });
      } else {
        console.log('热榜历史数据返回但格式不正确:', result);
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
        // 显示所有视频，不只是有封面的
        console.log('有封面的视频数:', result.data.video_analyses.filter((v: any) => v.cover_url).length);
        setVideoAnalyses(result.data.video_analyses);
        setSelectedIndex(0);
        return;
      }
      
      // 如果数据库没有数据，则尝试分析现有文件
      console.log('数据库中没有分析数据，尝试分析现有文件...');
      result = await api.hotComment.analyze();
      if (result.success && result.data) {
        // 显示所有视频，不只是有封面的
        setVideoAnalyses(result.data.video_analyses || []);
        if ((result.data.video_analyses || []).length > 0) {
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

  const generatePDFReport = () => {
    if (!selectedAnalysis) return;
    
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('请允许弹出窗口以生成PDF报告');
      return;
    }

    const analysis = selectedAnalysis.analysis;
    const sentimentLabel = getSentimentLabel(sentiment);
    const sentimentColor = sentiment === 'positive' ? '#10b981' : 
                          sentiment === 'negative' ? '#ef4444' : 
                          sentiment === 'controversial' ? '#f97316' : '#6b7280';

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>舆情分析报告 - ${selectedAnalysis.title || selectedAnalysis.file}</title>
        <style>
          body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            padding: 40px;
            background: #f5f5f5;
          }
          .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }
          .header {
            text-align: center;
            border-bottom: 3px solid #3370FF;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          .title {
            font-size: 28px;
            font-weight: bold;
            color: #1D2129;
            margin-bottom: 10px;
          }
          .subtitle {
            font-size: 14px;
            color: #86909C;
          }
          .section {
            margin-bottom: 30px;
          }
          .section-title {
            font-size: 18px;
            font-weight: bold;
            color: #1D2129;
            border-left: 4px solid #3370FF;
            padding-left: 12px;
            margin-bottom: 15px;
          }
          .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
          }
          .stat-card {
            background: #f7f8fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
          }
          .stat-label {
            font-size: 12px;
            color: #86909C;
            margin-bottom: 5px;
          }
          .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #1D2129;
          }
          .sentiment-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            background: ${sentimentColor};
          }
          .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
          }
          .table th, .table td {
            border: 1px solid #e5e7eb;
            padding: 8px 12px;
            text-align: left;
          }
          .table th {
            background: #f9fafb;
            font-weight: bold;
            color: #374151;
          }
          .table tr:nth-child(even) {
            background: #f9fafb;
          }
          .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #86909C;
            font-size: 12px;
          }
          @media print {
            body { background: white; }
            .container { box-shadow: none; }
          }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div class="title">舆情分析报告</div>
            <div class="subtitle">${selectedAnalysis.title || selectedAnalysis.file}</div>
            <div class="subtitle">视频ID: ${selectedAnalysis.aweme_id}</div>
          </div>

          <div class="section">
            <div class="section-title">一、概述</div>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-label">评论总数</div>
                <div class="stat-value">${analysis.total}</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">正面评价</div>
                <div class="stat-value">${analysis.sentiment.positive_rate}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">中性评价</div>
                <div class="stat-value">${analysis.sentiment.neutral_rate}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">负面评价</div>
                <div class="stat-value">${analysis.sentiment.negative_rate}%</div>
              </div>
            </div>
            <p><strong>舆情结论：</strong><span class="sentiment-badge">${sentimentLabel}</span></p>
          </div>

          <div class="section">
            <div class="section-title">二、情感分析</div>
            <table class="table">
              <tr>
                <th>情感类型</th>
                <th>数量</th>
                <th>占比</th>
              </tr>
              <tr>
                <td>正面</td>
                <td>${analysis.sentiment.positive}</td>
                <td>${analysis.sentiment.positive_rate}%</td>
              </tr>
              <tr>
                <td>中性</td>
                <td>${analysis.sentiment.neutral}</td>
                <td>${analysis.sentiment.neutral_rate}%</td>
              </tr>
              <tr>
                <td>负面</td>
                <td>${analysis.sentiment.negative}</td>
                <td>${analysis.sentiment.negative_rate}%</td>
              </tr>
            </table>
          </div>

          <div class="section">
            <div class="section-title">三、热门关键词 TOP 10</div>
            <table class="table">
              <tr>
                <th>排名</th>
                <th>关键词</th>
                <th>出现次数</th>
              </tr>
              ${analysis.hot_words.slice(0, 10).map((word, index) => `
                <tr>
                  <td>${index + 1}</td>
                  <td>${word[0]}</td>
                  <td>${word[1]}</td>
                </tr>
              `).join('')}
            </table>
          </div>

          <div class="section">
            <div class="section-title">四、高赞评论 TOP 5</div>
            <table class="table">
              <tr>
                <th>排名</th>
                <th>用户</th>
                <th>评论内容</th>
                <th>点赞数</th>
              </tr>
              ${analysis.top_comments.slice(0, 5).map((comment, index) => `
                <tr>
                  <td>${index + 1}</td>
                  <td>${comment.nickname}</td>
                  <td>${comment.text.substring(0, 50)}${comment.text.length > 50 ? '...' : ''}</td>
                  <td>${comment.digg_count}</td>
                </tr>
              `).join('')}
            </table>
          </div>

          <div class="section">
            <div class="section-title">五、用户活跃度</div>
            <table class="table">
              <tr>
                <th>指标</th>
                <th>数值</th>
              </tr>
              <tr>
                <td>总用户数</td>
                <td>${analysis.user_activity.total_users}</td>
              </tr>
              <tr>
                <td>人均评论数</td>
                <td>${analysis.user_activity.avg_comments_per_user.toFixed(2)}</td>
              </tr>
            </table>
          </div>

          ${analysis.topics && analysis.topics.topics && analysis.topics.topics.length > 0 ? `
          <div class="section">
            <div class="section-title">六、LDA 主题分析</div>
            <table class="table">
              <tr>
                <th>主题ID</th>
                <th>关键词</th>
              </tr>
              ${analysis.topics.topics.map((topic, index) => `
                <tr>
                  <td>主题${topic.topic_id}</td>
                  <td>${topic.keywords}</td>
                </tr>
              `).join('')}
            </table>
            <p><strong>模型：</strong>${analysis.topics.model}</p>
          </div>
          ` : ''}

          <div class="section">
            <div class="section-title">七、分析模型</div>
            <p><strong>情感分析模型：</strong>${analysis.sentiment.model}</p>
            ${analysis.topics && analysis.topics.model ? `<p><strong>主题分析模型：</strong>${analysis.topics.model}</p>` : ''}
          </div>

          <div class="footer">
            <p>报告生成时间：${new Date().toLocaleString('zh-CN')}</p>
            <p>数据来源：抖音热榜评论分析系统</p>
          </div>
        </div>
      </body>
      </html>
    `);

    printWindow.document.close();
    
    setTimeout(() => {
      printWindow.print();
    }, 500);
  };

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
          result += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)}%<br/>`;
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
      name: '变化率(%)',
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: {
        color: '#ffffff',
        formatter: '{value}%'
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#333',
          type: 'dashed'
        }
      }
    },
    // 系列数据 - 计算变化率
    series: hotHistoryData.series.map((s, idx) => {
      const colors = [
        '#9370DB', '#FF69B4', '#FFA500', '#3CB371', '#4169E1',
        '#9370DB', '#FF69B4', '#FFA500', '#3CB371', '#4169E1'
      ];
      
      // 计算变化率：以第一个时间点为基准
      const baseValue = s.data[0];
      const changeRateData = s.data.map((val: number | null | undefined) => {
        // 处理无效值
        if (baseValue === 0 || !baseValue) return 0;
        if (val === null || val === undefined || !val) return 0;
        
        // 计算变化率
        const changeRate = ((val - baseValue) / baseValue) * 100;
        
        // 处理异常值
        if (isNaN(changeRate) || !isFinite(changeRate)) {
          return 0;
        }
        
        return changeRate;
      });
      
      return {
        name: s.name,
        type: 'line',
        smooth: true,
        data: changeRateData,
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
          <div className="flex items-center gap-2">
            <button
              onClick={generatePDFReport}
              disabled={!selectedAnalysis}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2 text-sm"
              title="生成PDF报告"
            >
              <FileText size={16} />
              生成PDF报告
            </button>
            <button
              onClick={loadAnalyses}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2 text-sm"
            >
              🔄 刷新数据
            </button>
          </div>
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
                      {videoAnalysis.cover_url && videoAnalysis.cover_url.startsWith('/static/') ? (
                        <img
                          src={`http://127.0.0.1:8000${videoAnalysis.cover_url}`}
                          alt="封面"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      ) : null}
                      {/* 默认图标或错误占位 */}
                      <div className={`absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-slate-700 to-slate-800 ${videoAnalysis.cover_url && videoAnalysis.cover_url.startsWith('/static/') ? 'hidden' : ''}`}>
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
          {hotHistoryData ? (
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
          ) : (
            <div className="mb-6">
              <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4">
                <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-gradient-to-r from-red-500 to-orange-500 rounded-full"></span>
                  热榜热度趋势 TOP 10
                </h3>
                <div className="h-72 flex items-center justify-center">
                  <p className="text-slate-400">加载热榜历史数据中...</p>
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

          {/* LDA 主题分析 */}
          {selectedAnalysis.analysis.topics && (
            <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4 mb-6">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                LDA 主题分析
              </h3>
              <div className="space-y-4">
                {selectedAnalysis.analysis.topics.topics && selectedAnalysis.analysis.topics.topics.length > 0 ? (
                  selectedAnalysis.analysis.topics.topics.map((topic, index) => (
                    <div key={topic.topic_id} className="bg-slate-700/30 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-white">主题 {topic.topic_id}</h4>
                        <span className="text-xs text-gray-400">{topic.top_words.length} 个关键词</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {topic.top_words.map((word, idx) => (
                          <span key={idx} className="px-2 py-1 bg-slate-600/50 rounded-full text-xs text-gray-300">
                            {word}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="bg-slate-700/30 rounded-lg p-3 text-center">
                    <p className="text-gray-400">暂无主题分析数据</p>
                  </div>
                )}
                <div className="mt-4 text-sm text-gray-400">
                  <span className="font-medium text-gray-300">分析模型：</span>
                  {selectedAnalysis.analysis.topics.model}
                </div>
              </div>
            </div>
          )}

          {/* 情感分析模型信息 */}
          <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700/50 rounded-xl p-4 mb-6">
            <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-rose-500 rounded-full"></span>
              分析模型信息
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="text-sm font-medium text-white mb-1">情感分析模型</div>
                <div className="text-gray-300 text-sm">{selectedAnalysis.analysis.sentiment.model}</div>
              </div>
              {selectedAnalysis.analysis.topics && selectedAnalysis.analysis.topics.model && (
                <div className="bg-slate-700/30 rounded-lg p-3">
                  <div className="text-sm font-medium text-white mb-1">主题分析模型</div>
                  <div className="text-gray-300 text-sm">{selectedAnalysis.analysis.topics.model}</div>
                </div>
              )}
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
