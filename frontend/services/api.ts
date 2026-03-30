/**
 * 统一的 HTTP API 封装
 * 
 * 提供简洁的 API 调用方式，如：
 * - api.settings.get()
 * - api.task.start({ type, target, limit })
 * - api.aria2.config()
 */

import { AppSettings, TaskType, DouyinWork, LoginRequest, RegisterRequest, ChangePasswordRequest, AuthResponse, User } from '../types';

// ============================================================================
// 配置
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// ============================================================================
// 类型定义
// ============================================================================

/** API 错误 */
export class APIError extends Error {
  constructor(
    public statusCode: number,
    public detail: string
  ) {
    super(detail);
    this.name = 'APIError';
  }
}

/** 任务启动参数 */
export interface StartTaskParams {
  type: TaskType | string;
  target: string;
  limit?: number;
  filters?: Record<string, string>;
}

/** 任务响应 */
export interface TaskResponse {
  task_id: string;
  status: string;
}

/** 任务状态 */
export interface TaskStatus {
  id: string;
  type: string;
  target: string;
  status: 'running' | 'completed' | 'error';
  progress: number;
  result_count: number;
  error?: string;
  created_at: number;
  updated_at: number;
  aria2_conf?: string;
}

/** 健康状态 */
export interface HealthStatus {
  ready: boolean;
  aria2: boolean;
  config: boolean;
  error?: string;
}

/** Aria2 配置 */
export interface Aria2Config {
  host: string;
  port: number;
  secret: string;
}

/** 评论项（接口返回结构） */
export interface CommentItem {
  id: string;
  nickname: string;
  text: string;
  create_time: string;
  digg_count: number;
  reply_count: number;
  ip_label?: string;
  is_top?: boolean;
  is_hot?: boolean;
}

/** 抖音热榜项 */
export interface DouyinHotItem {
  ranks: number[];
  url: string;
  mobileUrl: string;
  hotValue: string;
}

// ============================================================================
// 核心请求函数
// ============================================================================

/**
 * 通用 fetch 封装
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new APIError(response.status, errorData.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

/**
 * GET 请求
 */
async function get<T>(endpoint: string): Promise<T> {
  return fetchAPI<T>(endpoint, { method: 'GET' });
}

/**
 * POST 请求
 */
async function post<T>(endpoint: string, body?: unknown): Promise<T> {
  return fetchAPI<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

// ============================================================================
// API 模块
// ============================================================================

export const api = {
  /** 基础 URL */
  baseUrl: API_BASE_URL,
  
  /** 健康检查 */
  health: () => get<HealthStatus>('/api/health'),
  
  /** 检查后端是否可用 */
  isAvailable: async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api`, {
        method: 'GET',
        signal: AbortSignal.timeout(2000),
      });
      return response.ok;
    } catch {
      return false;
    }
  },
  
  /** 等待后端就绪 */
  waitForReady: async (timeout: number = 30000): Promise<boolean> => {
    const startTime = Date.now();
    const checkInterval = 500;
    
    while (Date.now() - startTime < timeout) {
      if (await api.isAvailable()) {
        console.log(`[API] 后端服务已就绪 (${Date.now() - startTime}ms)`);
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, checkInterval));
    }
    
    console.error('[API] 连接超时');
    return false;
  },
  
  // ========================================================================
  // 用户认证
  // ========================================================================
  auth: {
    /** 用户注册 */
    register: (data: RegisterRequest) => 
      post<AuthResponse>('/api/auth/register', data),
    
    /** 用户登录 */
    login: (data: LoginRequest) => 
      post<AuthResponse>('/api/auth/login', data),
    
    /** 获取当前用户信息 */
    getCurrentUser: () => 
      get<User>('/api/auth/me'),
    
    /** 修改密码 */
    changePassword: (data: ChangePasswordRequest) => 
      post<{ status: string; message: string }>('/api/auth/change-password', data),
  },
  
  // ========================================================================
  // 设置管理
  // ========================================================================
  settings: {
    /** 获取当前设置 */
    get: () => get<AppSettings>('/api/settings'),
    
    /** 保存设置（支持部分更新） */
    save: (data: Partial<AppSettings>) => 
      post<{ status: string; message: string }>('/api/settings', data),
    
    /** 检查是否首次运行 */
    isFirstRun: async () => {
      const result = await get<{ is_first_run: boolean }>('/api/settings/first-run');
      return result.is_first_run;
    },
  },
  
  // ========================================================================
  // 任务管理
  // ========================================================================
  task: {
    /** 启动采集任务 */
    start: (params: StartTaskParams) => 
      post<TaskResponse>('/api/task/start', {
        type: params.type,
        target: params.target,
        limit: params.limit ?? 0,
        filters: params.filters ?? null,
      }),
    
    /** 获取任务状态 */
    status: (taskId?: string) => {
      const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : '';
      return get<TaskStatus[]>(`/api/task/status${query}`);
    },
    
    /** 获取任务结果 */
    results: (taskId: string) => 
      get<DouyinWork[]>(`/api/task/results/${encodeURIComponent(taskId)}`),
  },
  
  // ========================================================================
  // Aria2 管理
  // ========================================================================
  aria2: {
    /** 获取 Aria2 配置 */
    config: () => get<Aria2Config>('/api/aria2/config'),
    
    /** 获取 Aria2 状态 */
    status: async () => {
      const result = await get<{ connected: boolean }>('/api/aria2/status');
      return result.connected;
    },
    
    /** 启动 Aria2 服务 */
    start: () => post<{ status: string; message: string }>('/api/aria2/start'),
    
    /** 获取配置文件路径 */
    configPath: async (taskId?: string) => {
      const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : '';
      const result = await get<{ config_path: string }>(`/api/aria2/config-path${query}`);
      return result.config_path;
    },
  },
  
  // ========================================================================
  // 文件操作
  // ========================================================================
  file: {
    /** 打开文件夹 */
    openFolder: async (path: string) => {
      const result = await post<{ success: boolean }>('/api/file/open-folder', { folder_path: path });
      return result.success;
    },
    
    /** 检查文件是否存在 */
    checkExists: async (path: string) => {
      const result = await post<{ exists: boolean }>('/api/file/check-exists', { file_path: path });
      return result.exists;
    },
    
    /** 读取配置文件 */
    readConfig: async (path: string) => {
      const result = await post<{ content: string }>('/api/file/read-config', { file_path: path });
      return result.content;
    },

    /** 查找本地已下载文件 */
    findLocal: (workId: string) =>
      get<{ found: boolean; video_path: string | null; images: string[] | null }>(
        `/api/file/find-local/${encodeURIComponent(workId)}`
      ),

    /** 获取媒体文件 URL */
    getMediaUrl: (filePath: string) => {
      // 将路径分段编码，保留路径分隔符
      const encodedPath = filePath
        .split(/[/\\]/)
        .map(segment => encodeURIComponent(segment))
        .join('/');
      return `${API_BASE_URL}/api/file/media/${encodedPath}`;
    },
  },
  
  // ========================================================================
  // 评论
  // ========================================================================
  comment: {
    /** 获取评论列表（单页） */
    list: (awemeId: string, cursor = 0, count = 20) =>
      get<{ comments: CommentItem[]; cursor: number; has_more: boolean }>(
        `/api/comment/list?aweme_id=${encodeURIComponent(awemeId)}&cursor=${cursor}&count=${count}`
      ),
    /** 多页爬取评论并导出 CSV */
    crawl: (awemeId: string, maxCount = 500) =>
      post<{ comments: CommentItem[]; total: number; file: string | null; filename: string | null }>(
        '/api/comment/crawl',
        { aweme_id: awemeId, max_count: maxCount }
      ),
    /** 使用浏览器自动化爬取评论（API方式的备用方案） */
    crawlBrowser: (awemeId: string, videoUrl?: string, maxCount = 500) =>
      post<{ comments: CommentItem[]; total: number; file: string | null; method: string }>(
        '/api/comment/crawl-browser',
        { aweme_id: awemeId, video_url: videoUrl, max_count: maxCount }
      ),
    /** 分析评论数据并生成报告 */
    analyze: (csvFile?: string, generateReport = true) =>
      post<{
        analysis: Record<string, unknown>;
        csv_file: string;
        html_report?: string;
        wordcloud?: string;
      }>('/api/comment/analyze', { csv_file: csvFile, generate_report: generateReport }),
    /** 使用 Spark 预处理评论数据 */
    preprocess: (csvFile?: string) =>
      post<{
        success: boolean;
        message: string;
        input_file: string;
        output_path: string;
        total_records: number;
        processed_records: number;
      }>('/api/comment/preprocess', { csv_file: csvFile }),
    /** 获取最新的分析报告 */
    getAnalysisReport: (reportType: 'html' | 'wordcloud' = 'html') =>
      get<{ file_path: string; filename: string; created_at: string }>(
        `/api/comment/analysis-report?report_type=${reportType}`
      ),
  },

  // ========================================================================
  // 热搜
  // ========================================================================
  hot: {
    /** 获取抖音热榜 */
    douyin: () => get<Record<string, DouyinHotItem>>('/api/hot/douyin'),
    /** 刷新抖音热榜到数据库 */
    douyinRefreshDb: () => post<{ success: boolean; count: number; videos_count: number; message: string }>('/api/hot/douyin/refresh-db'),
    /** 从数据库获取抖音热榜 */
    douyinFromDb: (limit = 30) => get<{ success: boolean; from_db: boolean; data: any[]; is_stale?: boolean; time_ago?: string; latest_time?: string }>('/api/hot/douyin/from-db?limit=' + limit),
    /** 获取热榜历史数据（用于热度趋势图） */
    douyinHistory: (titleLimit = 10) => get<{ success: boolean; times: string[]; series: any[]; error?: string }>('/api/hot/douyin/history?title_limit=' + titleLimit),
  },

  // ========================================================================
  // 热榜评论
  // ========================================================================
  hotComment: {
    /** 爬取热榜视频评论 */
    crawl: (params: { 
      video_count: number; 
      comments_per_video: number; 
      save_to_csv: boolean; 
      save_to_db?: boolean; 
      video_ids?: string[]; 
      video_titles?: Record<string, string>;
      start_rank?: number; 
      end_rank?: number; 
    }) =>
      post<{ success: boolean; data: any; message: string }>('/api/hot-comment/crawl', params),
    
    /** 数据预处理（Spark 清洗） */
    dataPreprocess: () =>
      post<{ success: boolean; message: string }>('/api/hot-comment/data-preprocess'),
    
    /** 分析热榜评论数据 */
    analyze: (params?: { csv_files?: string[]; generate_report?: boolean }) =>
      post<{ success: boolean; data: any; message: string }>('/api/hot-comment/analyze', params || {}),
    
    /** 获取评论文件列表 */
    list: () => get<{ success: boolean; files: any[] }>('/api/hot-comment/list'),
    
    /** 获取分析报告 */
    getReport: (csvFile?: string) =>
      get<{ success: boolean; data: any }>(`/api/hot-comment/report${csvFile ? `?csv_file=${encodeURIComponent(csvFile)}` : ''}`),
    
    /** 从数据库获取分析结果 */
    getAnalysisFromDb: () =>
      get<{ success: boolean; data: any }>('/api/hot-comment/analysis/list'),
    
    /** 启动定时任务 */
    startScheduler: (params: { interval_hours: number; video_count: number; comments_per_video: number; save_to_db?: boolean }) =>
      post<{ success: boolean; message: string; data: any }>('/api/hot-comment/scheduler/start', params),
    
    /** 停止定时任务 */
    stopScheduler: () =>
      post<{ success: boolean; message: string }>('/api/hot-comment/scheduler/stop'),
    
    /** 获取定时任务状态 */
    getSchedulerStatus: () =>
      get<{ success: boolean; data: any }>('/api/hot-comment/scheduler/status'),
    
    /** 数据库相关 API */
    database: {
      /** 初始化数据库 */
      init: () => post<{ success: boolean; message: string }>('/api/hot-comment/database/init'),
      
      /** 获取数据库状态 */
      getStatus: () => get<{ success: boolean; data: any; message: string }>('/api/hot-comment/database/status'),
      
      /** 获取评论数据 */
      getComments: (params?: { aweme_id?: string; limit?: number; offset?: number; order_by?: string }) =>
        get<{ success: boolean; data: any; message: string }>(
          `/api/hot-comment/database/comments?aweme_id=${params?.aweme_id || ''}&limit=${params?.limit || 100}&offset=${params?.offset || 0}&order_by=${params?.order_by || 'digg_count'}`
        ),
      
      /** 获取统计信息 */
      getStatistics: () => get<{ success: boolean; data: any; message: string }>('/api/hot-comment/database/statistics'),
      
      /** 清空数据 */
      clear: (table?: string) => post<{ success: boolean; message: string }>(`/api/hot-comment/database/clear${table ? `?table=${table}` : ''}`),
    },
  },

  // ========================================================================
  // 系统工具
  // ========================================================================
  system: {
    /** 获取剪贴板内容 */
    clipboard: async () => {
      const result = await get<{ text: string }>('/api/system/clipboard');
      return result.text;
    },
    
    /** 打开外部链接（GUI 模式使用） */
    openUrl: (url: string) => 
      post<{ status: string; message: string }>('/api/system/open-url', { url }),

    /** 通过登录获取 Cookie（仅 GUI 模式） */
    cookieLogin: () =>
      post<{ success: boolean; cookie: string; user_agent: string; error: string }>(
        '/api/system/cookie-login'
      ),
  },
};

export default api;
