import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthModal } from './components/AuthModal';
import { DetailModal } from './components/DetailModal';
import { ErrorBoundary, LightErrorBoundary } from './components/ErrorBoundary';
import { HotCommentAnalyzer } from './components/HotCommentAnalyzer';
import { HotCommentDashboard } from './components/HotCommentDashboard';
import { HotSearchDashboard } from './components/HotSearchDashboard';
import { LogPanel } from './components/LogPanel';
import { SettingsModal } from './components/SettingsModal';
import { Sidebar } from './components/Sidebar';
import { ToastContainer, toast } from './components/Toast';
import { UserManagement } from './components/UserManagement';
import { WelcomeWizard } from './components/WelcomeWizard';
import { WorkCard } from './components/WorkCard';
import { bridge } from './services/bridge';
import { sseClient, TaskResultEvent, TaskStatusEvent, TaskErrorEvent } from './services/sseClient';
import { logger } from './services/logger';
import { DouyinWork, TaskType, User } from './types';

// 延迟加载虚拟滚动库（这些库比较大）
import {
  ChevronDown, ChevronUp,
  Download,
  Infinity as InfinityIcon, Layers,
  Loader2,
  Search,
  Sparkles
} from 'lucide-react';
import memoize from 'memoize-one';
import AutoSizer from 'react-virtualized-auto-sizer';
import { FixedSizeList } from 'react-window';

// --- 虚拟滚动列表辅助工具 ---

/**
 * 行数据接口
 * 用于传递给虚拟列表的每一行渲染器
 */
interface RowData {
  items: DouyinWork[];                          // 作品列表
  columnCount: number;                          // 每行列数
  width: number;                                // 容器宽度
  onClick: (work: DouyinWork) => void;          // 点击作品的回调
}

/**
 * 创建行数据的辅助函数
 * 使用 memoize-one 确保只在依赖项变化时重新创建，避免不必要的重渲染
 */
const createItemData = memoize(
  (
    items: DouyinWork[],
    columnCount: number,
    width: number,
    onClick: (work: DouyinWork) => void
  ) => ({
    items,
    columnCount,
    width,
    onClick,
  }),
  // 自定义比较函数
  (newArgs, oldArgs) => {
    const [newItems, newColumnCount, newWidth, newOnClick] = newArgs;
    const [oldItems, oldColumnCount, oldWidth, oldOnClick] = oldArgs;

    // 基本类型比较
    if (newColumnCount !== oldColumnCount) return false;
    if (newWidth !== oldWidth) return false;
    if (newOnClick !== oldOnClick) return false;
    if (newItems !== oldItems) return false;

    return true;
  }
);

/**
 * 根据容器宽度计算列数（响应式网格）
 * @param width 容器宽度（像素）
 * @returns 列数
 */
const getColumnCount = (width: number) => {
  if (width >= 1920) return 5; // 超大屏幕
  if (width >= 1600) return 4; // 大屏幕
  if (width >= 1280) return 4; // xl 标准窗口
  if (width >= 1024) return 3; // lg 中等屏幕
  if (width >= 768) return 2;  // md 平板
  return 2;                     // 小屏幕/手机
};

/**
 * 虚拟列表的行渲染器
 * 定义在组件外部以防止每次渲染时重新挂载
 * 
 * @param index 行索引
 * @param style 由 FixedSizeList 提供的样式（包含位置信息）
 * @param data 行数据（包含作品列表和回调函数）
 */
const Row: React.FC<{ index: number; style: any; data: RowData }> = ({ index, style, data }) => {
  const { items, columnCount, width, onClick } = data;
  const startIndex = index * columnCount;
  const rowItems = items.slice(startIndex, startIndex + columnCount);

  return (
    <div style={style} className="grid gap-6 p-6 box-border">
      <div
        className="grid gap-6 w-full"
        style={{
          gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
        }}
      >
        {rowItems.map((work) => (
          <WorkCard key={work.id} work={work} onClick={() => onClick(work)} />
        ))}
        {/* 填充空白单元格 */}
        {Array.from({ length: columnCount - rowItems.length }).map((_, i) => (
          <div key={`empty-${index}-${i}`} className="invisible" />
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// 主组件
// ============================================================================

export const App: React.FC = () => {
  // --- 输入相关状态 ---
  const [inputValue, setInputValue] = useState('');  // 当前输入框内容
  const [inputError, setInputError] = useState(false);  // 输入框错误状态
  const inputRef = useRef<HTMLInputElement>(null);  // 输入框 DOM 引用

  // --- 任务相关状态 ---
  const [activeTab, setActiveTab] = useState<TaskType | string>(TaskType.AWEME);  // 当前选中的任务类型
  const [maxCount, setMaxCount] = useState<number>(0);  // 0 表示不限制数量
  const [showLimitMenu, setShowLimitMenu] = useState(false);  // 是否显示数量限制菜单
  const limitMenuRef = useRef<HTMLDivElement>(null);  // 数量限制菜单的引用，用于检测外部点击

  // --- 采集结果相关状态 ---
  const [isLoading, setIsLoading] = useState(false);  // 是否正在采集
  const [results, setResults] = useState<DouyinWork[]>([]);  // 采集结果列表
  const [selectedWorkId, setSelectedWorkId] = useState<string | null>(null);  // 当前查看详情的作品 ID
  const [resultsTaskType, setResultsTaskType] = useState<TaskType | null>(null);  // 记录结果对应的任务类型
  const [savedInputVal, setSavedInputVal] = useState('');  // 保存采集时的输入框内容
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);  // 保存当前采集任务的 ID

  // --- 热榜相关状态 ---
  const [autoCrawlVideoId, setAutoCrawlVideoId] = useState<string | null>(null);
  const [autoCrawlTitle, setAutoCrawlTitle] = useState<string | null>(null);
  const [dashboardRefreshTrigger, setDashboardRefreshTrigger] = useState(0);

  // --- 模态框状态 ---
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showWelcomeWizard, setShowWelcomeWizard] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [requireAuth, setRequireAuth] = useState(true);  // 强制登录标志

  // --- 用户认证状态 ---
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);



  /**
   * 计算当前选中作品在结果列表中的索引
   * 用于详情模态框的上一个/下一个导航
   */
  const selectedWorkIndex = useMemo(() => {
    return selectedWorkId ? results.findIndex(r => r.id === selectedWorkId) : -1;
  }, [selectedWorkId, results]);

  // 当前查看详情的作品对象
  const selectedWork = selectedWorkIndex >= 0 ? results[selectedWorkIndex] : null;

  /**
   * 在详情模态框中导航到上一个或下一个作品
   * @param direction 导航方向
   */
  const navigateWork = (direction: 'next' | 'prev') => {
    if (selectedWorkIndex === -1) return;
    const newIndex = direction === 'next' ? selectedWorkIndex + 1 : selectedWorkIndex - 1;
    if (newIndex >= 0 && newIndex < results.length) {
      setSelectedWorkId(results[newIndex].id);
    }
  };

  /**
   * 处理从热榜点击爬取单个视频
   */
  const handleAnalyzeHotItem = useCallback((videoId: string, title: string) => {
    setAutoCrawlVideoId(videoId);
    setAutoCrawlTitle(title);
  }, []);

  /**
   * 处理认证成功
   */
  const handleAuthSuccess = useCallback((user: User, newToken: string) => {
    setCurrentUser(user);
    setToken(newToken);
    setRequireAuth(false);
    setIsAuthModalOpen(false);  // 关闭认证模态框
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('token', newToken);
    logger.success(`欢迎 ${user.username} 加入`);
    toast.success('登录成功');
  }, []);

  /**
   * 处理用户登出
   */
  const handleLogout = useCallback(() => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setCurrentUser(null);
    setToken(null);
    setRequireAuth(true);
    logger.info('用户已登出');
    toast.info('已退出登录');
  }, []);

  /**
   * 初始化时检查用户登录状态
   */
  useEffect(() => {
    // 检查本地存储中的用户信息和token
    const storedUser = localStorage.getItem('user');
    const storedToken = localStorage.getItem('token');
    
    if (storedUser && storedToken) {
      try {
        const user = JSON.parse(storedUser);
        setCurrentUser(user);
        setToken(storedToken);
        setRequireAuth(false);
      } catch (error) {
        // 解析失败，清除本地存储
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        setCurrentUser(null);
        setToken(null);
        setRequireAuth(true);
      }
    } else {
      setRequireAuth(true);
    }
  }, []);

  /**
   * 处理用户手动切换任务类型
   * 不清空数据，通过 resultsTaskType 控制显示
   */
  const handleTabChange = useCallback((newTab: TaskType | string) => {
    if (newTab !== activeTab) {
      setActiveTab(newTab);
      // 切换任务类型时，清空之前的采集结果
      setResults([]);
      setResultsTaskType(null);
      setInputValue('');
      setSelectedWorkId(null);
    }
  }, [activeTab]);

  // 使用 ref 保存最新的回调函数，避免 SSE 重复订阅
  const handleTaskResultRef = React.useRef<(event: TaskResultEvent) => void>(() => {});
  const handleTaskStatusRef = React.useRef<(event: TaskStatusEvent) => void>(() => {});
  const handleTaskErrorRef = React.useRef<(event: TaskErrorEvent) => void>(() => {});

  /**
   * 处理 SSE 任务状态事件
   */
  const handleTaskStatus = useCallback((event: TaskStatusEvent) => {
    console.log('[DEBUG] 收到任务状态:', event);
    // 如果是当前任务的状态更新
    if (event.task_id === currentTaskId) {
      // 如果任务已开始采集，更新状态
      if (event.status === 'running') {
        setIsLoading(true);
      } else if (event.status === 'completed' || event.status === 'error') {
        // 任务完成或出错时，停止加载状态
        setIsLoading(false);
        console.log('[DEBUG] 任务状态更新为:', event.status, '停止加载');

      }
    }
  }, [currentTaskId]);

  /**
   * 处理 SSE 任务结果事件
   */
  const handleTaskResult = useCallback((event: TaskResultEvent) => {
    console.log('[DEBUG] 收到任务结果:', event.task_id, '数据数量:', event.data?.length || 0);
    console.log('[DEBUG] 当前 currentTaskId:', currentTaskId);
    console.log('[DEBUG] 数据内容:', event.data);
    
    // 检查是否是当前任务 - 直接使用 currentTaskId
    if (event.task_id !== currentTaskId) {
      console.log('[DEBUG] 忽略非当前任务的结果:', event.task_id, '(当前:', currentTaskId + ')');
      return;
    }
    
    console.log('[INFO] 处理当前任务', event.task_id, '的结果');
    
    // 追加新的采集结果
    setResults(prev => {
      // 确保 event.data 存在且是数组
      const works = event.data || [];
      if (!Array.isArray(works)) {
        console.warn('[WARN] 收到非数组格式的任务结果数据');
        return prev;
      }
      // 过滤掉已存在的作品（根据 ID 去重）
      const newWorks = works.filter(
        newWork => !prev.some(existing => existing.id === newWork.id)
      );
      console.log('[INFO] 新增', newWorks.length, '条数据，当前总数:', prev.length + newWorks.length);
      console.log('[INFO] 新增数据详情:', newWorks);
      return [...prev, ...newWorks];
    });
    
    // 更新任务类型和输入值
    setResultsTaskType(activeTab);
    setSavedInputVal(inputValue);
  }, [currentTaskId, activeTab, inputValue]);

  /**
   * 处理 SSE 任务错误事件
   */
  const handleTaskError = useCallback((event: TaskErrorEvent) => {
    if (event.task_id === currentTaskId) {
      setIsLoading(false);
      toast.error(`任务失败：${event.error}`);
      logger.error(`任务 ${event.task_id} 失败：${event.error}`);
    }
  }, [currentTaskId]);

  // 更新 ref 中的回调函数
  useEffect(() => {
    handleTaskResultRef.current = handleTaskResult;
    handleTaskStatusRef.current = handleTaskStatus;
    handleTaskErrorRef.current = handleTaskError;
  }, [handleTaskResult, handleTaskStatus, handleTaskError]);

  /**
   * 监听 SSE 消息（只连接一次，不重复订阅）
   */
  useEffect(() => {
    // 连接 SSE 服务器（只在组件挂载时连接一次）
    sseClient.connect('http://localhost:8000/api/events');

    // 创建稳定的包装函数
    const wrappedHandleResult = (event: TaskResultEvent) => handleTaskResultRef.current(event);
    const wrappedHandleStatus = (event: TaskStatusEvent) => handleTaskStatusRef.current(event);
    const wrappedHandleError = (event: TaskErrorEvent) => handleTaskErrorRef.current(event);

    // 订阅事件（只订阅一次）
    const unsubResult = sseClient.onTaskResult(wrappedHandleResult);
    const unsubStatus = sseClient.onTaskStatus(wrappedHandleStatus);
    const unsubError = sseClient.onTaskError(wrappedHandleError);

    // 组件卸载时取消订阅（但不断开连接，因为其他组件可能还需要）
    return () => {
      unsubResult();
      unsubStatus();
      unsubError();
    };
  }, []); // 空依赖数组，只执行一次



  /**
   * 处理开始爬取按钮点击
   */
  const handleStartCrawl = useCallback(async () => {
    // 验证输入
    if (!inputValue.trim()) {
      setInputError(true);
      toast.error('请输入作品链接或ID');
      return;
    }

    // 检查是否是用户管理页面
    if (activeTab === 'user_management') {
      return;
    }

    setInputError(false);
    setIsLoading(true);
    setResults([]);  // 清空旧数据
    setSelectedWorkId(null);

    try {
      // 启动任务
      const target = inputValue.trim();
      const result = await bridge.startTask(activeTab as TaskType, target, maxCount || 0);

      if (result.task_id) {
        setCurrentTaskId(result.task_id);
        logger.info(`任务 ${result.task_id} 已创建`);
      } else {
        throw new Error('任务创建失败');
      }
    } catch (error: any) {
      setIsLoading(false);
      toast.error(`创建任务失败：${error.message}`);
      logger.error(`创建任务失败：${error.message}`);
    }
  }, [inputValue, activeTab, maxCount]);

  /**
   * 处理输入框键盘事件
   */
  const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isLoading) {
      handleStartCrawl();
    }
  }, [handleStartCrawl, isLoading]);

  /**
   * 处理作品点击事件
   */
  const handleWorkClick = useCallback((work: DouyinWork) => {
    setSelectedWorkId(work.id);
  }, []);



  /**
   * 根据当前任务类型返回输入框的占位符文本
   */
  const getPlaceholder = () => {
    switch (activeTab) {
      case TaskType.AWEME:
        return '支持：长链接、短链接、纯数字 ID';
      case TaskType.MUSIC:
        return '支持：长链接、短链接、纯数字 ID';
      case TaskType.MIX:
        return '支持：长链接、短链接、纯数字 ID';
      case TaskType.POST:
        return '支持：长链接、短链接、SecUid';
      case TaskType.FAVORITE:
        return '支持：长链接、短链接、SecUid';
      case TaskType.COLLECTION:
        return '支持：长链接、短链接、SecUid';
      default:
        return '请输入目标链接';
    }
  };

  /**
   * 增加采集数量限制
   */
  const incrementMaxCount = () => setMaxCount(prev => (prev || 0) + 1);

  /**
   * 减少采集数量限制（最小为 0）
   */
  const decrementMaxCount = () => setMaxCount(prev => Math.max(0, (prev || 0) - 1));

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        logger.error(`应用错误：${error.message}`);
        console.error('错误详情:', error, errorInfo);
      }}
    >
      {/* 强制登录界面 */}
      {requireAuth && (
        <div 
          className="fixed inset-0 flex items-stretch z-50"
          style={{
            backgroundImage: 'url(/login-bg.png)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat'
          }}
        >
          <div className="absolute inset-0 bg-white/20"></div>
          
          <div className="relative z-10 w-full flex justify-end items-center h-full px-16 py-8">
            {/* 右侧登录表单 */}
            <div className="w-full md:w-[600px]">
              <div className="bg-white rounded-2xl shadow-xl p-12">
                {/* 系统标题 */}
                <div className="mb-10 text-center">
                  <h1 className="text-2xl font-bold text-gray-900 mb-3">抖音舆情分析系统</h1>
                  <p className="text-sm text-gray-600">洞察舆情，把握趋势</p>
                </div>
                
                <AuthModal
                  isOpen={true}
                  onClose={() => {}}
                  onAuthSuccess={handleAuthSuccess}
                  isForced={true}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 主界面 */}
      {!requireAuth && (
        <>
          <div className="flex h-screen bg-[#F8F9FB] overflow-hidden font-sans text-gray-900 selection:bg-blue-100 selection:text-blue-900">
            <LightErrorBoundary fallbackMessage="侧边栏加载失败">
              <Sidebar
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onOpenSettings={() => setIsSettingsOpen(true)}
                showLogs={showLogs}
                setShowLogs={setShowLogs}
                currentUser={currentUser}
                onOpenAuth={() => setIsAuthModalOpen(true)}
                onLogout={handleLogout}
              />
            </LightErrorBoundary>

            {/* 根据 activeTab 显示不同的主内容区域 */}
            {activeTab === TaskType.HOT_SEARCH ? (
              <LightErrorBoundary fallbackMessage="热榜页面加载失败">
                <HotSearchDashboard setActiveTab={handleTabChange} onAnalyzeHotItem={handleAnalyzeHotItem} />
              </LightErrorBoundary>
            ) : activeTab === TaskType.HOT_COMMENT ? (
              <LightErrorBoundary fallbackMessage="热榜评论分析页面加载失败">
                <HotCommentAnalyzer setActiveTab={handleTabChange} autoCrawlVideoId={autoCrawlVideoId} autoCrawlTitle={autoCrawlTitle} />
              </LightErrorBoundary>
            ) : activeTab === TaskType.HOT_COMMENT_DASHBOARD ? (
              <LightErrorBoundary fallbackMessage="热榜评论大屏页面加载失败">
                <HotCommentDashboard refreshTrigger={dashboardRefreshTrigger} />
              </LightErrorBoundary>
            ) : activeTab === 'user_management' ? (
              <LightErrorBoundary fallbackMessage="用户管理页面加载失败">
                <UserManagement />
              </LightErrorBoundary>
            ) : (
              <main className="flex-1 flex flex-col min-w-0 relative">
                {/* Sticky Header */}
                <div className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-gray-200/60 shadow-sm transition-all">
                  <div className="max-w-7xl mx-auto w-full px-8 py-5">
                    {true && (
                      <>
                        <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2 tracking-tight">
                          数据采集
                        </h2>

                        {/* 搜索框 */}
                        <div className="flex gap-3">
                          <div className="flex-1">
                            <div className={`relative flex group shadow-sm rounded-xl border transition-all bg-white z-20 ${inputError ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : 'border-gray-200 focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500'
                              }`}>
                              <div className="pl-4 flex items-center pointer-events-none bg-transparent">
                                <Search className={`h-5 w-5 transition-colors ${inputError ? 'text-red-500' : 'text-gray-400 group-focus-within:text-blue-500'
                                  }`} />
                              </div>
                              <input
                                ref={inputRef}
                                type="text"
                                className={`w-full px-4 py-3 bg-transparent border-0 outline-none text-gray-700 placeholder-gray-400 rounded-xl ${inputError ? 'text-red-500 placeholder-red-300' : ''
                                  }`}
                                placeholder={getPlaceholder()}
                                value={inputValue}
                                onChange={(e) => {
                                  setInputValue(e.target.value);
                                  if (inputError) setInputError(false);
                                }}
                                onKeyDown={handleInputKeyDown}
                                disabled={isLoading}
                              />
                              <div className="pr-2 flex items-center gap-1">
                                <button
                                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                  onClick={async () => {
                                    try {
                                      const text = await bridge.getClipboardText();
                                      if (text) {
                                        setInputValue(text);
                                        if (inputError) setInputError(false);
                                        toast.success('剪贴板内容已粘贴');
                                      }
                                    } catch (error: any) {
                                      toast.error('读取剪贴板失败');
                                    }
                                  }}
                                  title="从剪贴板粘贴"
                                >
                                  <Download className="h-5 w-5 text-gray-400 rotate-180" />
                                </button>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            {/* 数量限制 */}
                            <div className="relative" ref={limitMenuRef}>
                              <button
                                className="px-4 py-3 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50 transition-all flex items-center gap-2 shadow-sm"
                                onClick={() => setShowLimitMenu(!showLimitMenu)}
                                title="设置采集数量"
                              >
                                <Layers className="h-5 w-5 text-gray-500" />
                                <span className="font-medium text-gray-700">
                                  {maxCount === 0 ? <InfinityIcon className="h-5 w-5" /> : maxCount}
                                </span>
                                <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showLimitMenu ? 'rotate-180' : ''}`} />
                              </button>

                              {/* 数量限制下拉菜单 */}
                              {showLimitMenu && (
                                <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-gray-100 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                                  <div className="px-4 py-3 border-b border-gray-100">
                                    <div className="text-sm font-medium text-gray-700">采集数量限制</div>
                                    <div className="text-xs text-gray-500 mt-1">设置单次采集的最大作品数量</div>
                                  </div>
                                  <div className="p-3">
                                    <div className="flex items-center justify-between gap-2">
                                      <button
                                        className="flex-1 py-2 px-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center"
                                        onClick={decrementMaxCount}
                                        disabled={!maxCount || maxCount <= 1}
                                      >
                                        <ChevronDown className="h-5 w-5 text-gray-600" />
                                      </button>
                                      <div className="flex-1 text-center">
                                        <div className="text-lg font-bold text-gray-700">
                                          {maxCount === 0 ? '∞' : maxCount}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                          {maxCount === 0 ? '不限制' : '作品数量'}
                                        </div>
                                      </div>
                                      <button
                                        className="flex-1 py-2 px-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center"
                                        onClick={incrementMaxCount}
                                      >
                                        <ChevronUp className="h-5 w-5 text-gray-600" />
                                      </button>
                                    </div>
                                    {maxCount !== 0 && (
                                      <button
                                        className="w-full mt-3 py-2 px-3 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors text-sm font-medium"
                                        onClick={() => setMaxCount(0)}
                                      >
                                        设为不限制
                                      </button>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>

                            <button
                              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-medium rounded-xl transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                              onClick={handleStartCrawl}
                              disabled={isLoading || !inputValue.trim()}
                            >
                              {isLoading ? (
                                <Loader2 size={20} className="animate-spin" />
                              ) : (
                                <Sparkles size={20} />
                              )}
                              <span>{isLoading ? '采集中...' : '开始采集'}</span>
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto">
                  <div className="max-w-7xl mx-auto w-full px-8 py-6">
                    {isLoading ? (
                      <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 size={48} className="animate-spin text-blue-500 mb-4" />
                        <p className="text-gray-500 font-medium">正在采集数据...</p>
                      </div>
                    ) : results.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-20 text-center">
                        <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                          <Search size={48} className="text-gray-400" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-700 mb-2">暂无数据</h3>
                        <p className="text-gray-500 max-w-md">
                          {activeTab === TaskType.SEARCH
                            ? '请输入关键词开始搜索，例如：美食、旅游、科技'
                            : '请输入链接开始采集作品信息'}
                        </p>
                      </div>
                    ) : (
                      <div className="h-full">
                        <div className="absolute top-2 right-2 bg-blue-100 text-blue-800 px-3 py-1 rounded text-sm font-medium z-10">
                          当前数据：{results.length} 条
                        </div>
                        
                        {/* 简单渲染，不使用虚拟列表 */}
                        <div className="p-6">
                          <div 
                            className="grid gap-6 w-full"
                            style={{
                              gridTemplateColumns: `repeat(${getColumnCount(window.innerWidth)}, minmax(0, 1fr))`,
                            }}
                          >
                            {results.map((work) => (
                              <WorkCard 
                                key={work.id} 
                                work={work} 
                                onClick={() => handleWorkClick(work)} 
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <LightErrorBoundary fallbackMessage="详情弹窗加载失败">
                  <DetailModal
                  work={selectedWork}
                  onClose={() => setSelectedWorkId(null)}
                  onPrev={() => navigateWork('prev')}
                  onNext={() => navigateWork('next')}
                  hasPrev={selectedWorkIndex > 0}
                  hasNext={selectedWorkIndex < results.length - 1}
                />
                </LightErrorBoundary>
              </main>
            )}

            {/* 全局组件：Toast 容器 - 在所有面板中都显示 */}
            <ToastContainer />

            {/* 全局组件：设置弹窗 */}
            <LightErrorBoundary fallbackMessage="设置面板加载失败">
              <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
            </LightErrorBoundary>

            {/* 全局组件：日志面板 */}
            <LightErrorBoundary fallbackMessage="日志面板加载失败">
              <LogPanel isOpen={showLogs} onToggle={() => setShowLogs(!showLogs)} />
            </LightErrorBoundary>

            {/* 欢迎向导 */}
            <LightErrorBoundary fallbackMessage="欢迎向导加载失败">
              <WelcomeWizard
                isOpen={showWelcomeWizard}
                onClose={() => setShowWelcomeWizard(false)}
                onComplete={() => {
                  setShowWelcomeWizard(false);
                  logger.info("欢迎向导已完成");
                  toast.success("配置已保存，欢迎使用！");
                }}
              />
            </LightErrorBoundary>

            {/* 认证模态框（用于侧边栏点击"用户登录"） */}
            <LightErrorBoundary fallbackMessage="认证面板加载失败">
              <AuthModal
                isOpen={isAuthModalOpen}
                onClose={() => setIsAuthModalOpen(false)}
                onAuthSuccess={handleAuthSuccess}
              />
            </LightErrorBoundary>
          </div>
        </>
      )}
    </ErrorBoundary>
  );
};
