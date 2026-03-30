
export enum TaskType {
  AWEME = 'aweme',           // 单个作品
  POST = 'post',             // 用户主页作品
  FAVORITE = 'favorite',     // 用户喜欢
  COLLECTION = 'collection', // 用户收藏
  MUSIC = 'music',           // 音乐原声
  HASHTAG = 'hashtag',       // 话题挑战
  MIX = 'mix',               // 合集
  SEARCH = 'search',         // 关键词搜索
  FOLLOWING = 'following',   // 用户关注
  FOLLOWER = 'follower',     // 用户粉丝
  DOWNLOAD_MANAGER = 'download_manager', // 下载管理
  HOT_SEARCH = 'hot_search', // 热搜功能
  HOT_COMMENT = 'hot_comment', // 热榜评论分析
  HOT_COMMENT_DASHBOARD = 'hot_comment_dashboard', // 热榜评论大屏
}

export interface DouyinWork {
  id: string;
  desc: string;
  author: {
    nickname: string;
    avatar: string;
    uid: string;
    unique_id?: string; // 抖音号
    short_id?: string; // 短ID
  };
  type: 'video' | 'image';
  cover: string;
  videoUrl?: string; // For video type
  images?: string[]; // For image type
  music?: {
    id: string;
    title: string;
    url: string;
    cover: string;
  };
  stats: {
    digg_count: number;
    comment_count: number;
    share_count: number;
  };
  create_time: string;
  duration?: number; // 视频时长（毫秒）
}

export interface DownloadProgress {
  id: string;
  work_id?: string;
  filename: string;
  progress: number; // 0-100
  status: 'pending' | 'downloading' | 'completed' | 'error' | 'canceled' | 'paused';
  speed: number; // B/s
  path: string;
  error?: string;
  totalLength: number;
  completedLength: number;
}

export interface AppSettings {
  cookie: string;
  userAgent: string;
  downloadPath: string;
  maxRetries: number;
  maxConcurrency: number;
  enableIncrementalFetch: boolean;
  aria2Host: string;
  aria2Port: number;
  aria2Secret: string;
}

export interface GlobalDownloadStat {
  downloadSpeed: string;
  numActive: string;
  numWaiting: string;
  numStopped: string;
}

// ============================================================================
// 用户认证相关类型
// ============================================================================

export interface User {
  id: number;
  username: string;
  email?: string;
  phone?: string;
  avatar?: string;
  role: 'user' | 'admin';
  status: 'active' | 'inactive' | 'banned';
  last_login?: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}