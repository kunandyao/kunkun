/**
 * 前后端通信桥接服务
 * 统一使用 HTTP API 与后端通信
 */

import { AppSettings, TaskType } from '../types';
import { handleError } from '../utils/errorHandler';
import { logger } from './logger';
import { sseClient } from './sseClient';
import api from './api';

export type RunMode = 'gui' | 'web';

export function detectRunMode(): RunMode {
  if (typeof window === 'undefined') return 'web';
  if ('pywebview' in window) return 'gui';
  if (navigator.userAgent.toLowerCase().includes('pywebview')) return 'gui';
  return 'web';
}

let _runMode: RunMode | null = null;
export function getRunMode(): RunMode {
  if (_runMode === null) {
    _runMode = detectRunMode();
    console.log('[Bridge] mode: ' + _runMode);
  }
  return _runMode;
}

export function isGUIMode(): boolean {
  return getRunMode() === 'gui';
}

export interface Bridge {
  isAvailable: () => boolean;
  waitForReady: (timeout?: number) => Promise<boolean>;
  startTask: (type: TaskType, target: string, limit?: number, filters?: Record<string, string>) => Promise<{ task_id: string; status: string }>;
  openExternal: (url: string) => void;
  getSettings: () => Promise<AppSettings>;
  saveSettings: (settings: AppSettings) => Promise<void>;
  selectFolder: () => Promise<string>;
  subscribeToLogs: (callback: (log: any) => void) => Promise<() => void>;
  getTaskStatus: (taskId?: string) => Promise<any[]>;
  getAria2Config: () => Promise<{ host: string; port: number; secret: string }>;
  isFirstRun: () => Promise<boolean>;
  startAria2: () => Promise<void>;
  getTaskResults: (taskId: string) => Promise<any[]>;
  getClipboardText: () => Promise<string>;
  readConfigFile: (filePath: string) => Promise<string>;
  getAria2ConfigPath: (taskId?: string) => Promise<string>;
  checkFileExists: (filePath: string) => Promise<boolean>;
  openFolder: (folderPath: string) => Promise<boolean>;
  cookieLogin: () => Promise<{ success: boolean; cookie: string; user_agent: string; error: string }>;
  findLocalFile: (workId: string) => Promise<{ found: boolean; video_path: string | null; images: string[] | null }>;
  getMediaUrl: (filePath: string) => string;
  /** 爬取作品评论（多页）并导出 CSV */
  crawlComments: (awemeId: string, maxCount?: number) => Promise<{ comments: any[]; total: number; file: string | null; filename: string | null }>;
  /** 使用浏览器自动化爬取评论（API方式的备用方案） */
  crawlCommentsBrowser: (awemeId: string, videoUrl?: string, maxCount?: number) => Promise<{ comments: any[]; total: number; file: string | null; method: string }>;
  /** 分析评论数据并生成报告 */
  analyzeComments: (csvFile?: string, generateReport?: boolean) => Promise<{ analysis: Record<string, unknown>; csv_file: string; html_report?: string; wordcloud?: string }>;
  /** 使用 Spark 预处理评论数据 */
  preprocessComments: (csvFile?: string) => Promise<{ success: boolean; message: string; input_file: string; output_path: string; total_records: number; processed_records: number }>;
  /** 获取最新的分析报告 */
  getAnalysisReport: (reportType?: 'html' | 'wordcloud') => Promise<{ file_path: string; filename: string; created_at: string }>;
}

export const bridge: Bridge = {
  isAvailable: () => true,

  waitForReady: async (timeout = 30000) => {
    console.log('[Bridge] waiting...');
    const ready = await api.waitForReady(timeout);
    if (ready) {
      sseClient.connect(api.baseUrl + '/api/events');
      await new Promise(r => setTimeout(r, 500));
      console.log(sseClient.isConnected() ? '[Bridge] SSE OK' : '[Bridge] SSE failed');
    }
    return ready;
  },

  startTask: async (type, target, limit = 0, filters) => {
    try {
      logger.api.request('start task', { type, target, limit, filters });
      const result = await api.task.start({ type, target, limit, filters });
      logger.api.response('task started', { taskId: result.task_id });
      return result;
    } catch (error) {
      handleError(error, { type, target, limit, filters }, { customMessage: 'task start failed' });
      throw error;
    }
  },

  openExternal: (url) => {
    if (isGUIMode()) {
      api.system.openUrl(url).catch(() => window.open(url, '_blank'));
    } else {
      window.open(url, '_blank');
    }
  },

  getSettings: async () => {
    try {
      return await api.settings.get();
    } catch (error) {
      handleError(error, {}, { customMessage: 'get settings failed', showToast: false });
      throw error;
    }
  },

  saveSettings: async (settings) => {
    try {
      logger.api.request('save settings', settings);
      await api.settings.save(settings);
    } catch (error) {
      handleError(error, settings, { customMessage: 'save settings failed' });
      throw error;
    }
  },

  selectFolder: async () => {
    if (isGUIMode()) {
      try {
        const settings = await api.settings.get();
        return settings.downloadPath || '';
      } catch { return ''; }
    }
    return '';
  },

  subscribeToLogs: async (callback) => sseClient.onLog(callback),

  getTaskStatus: async (taskId) => {
    try {
      return await api.task.status(taskId);
    } catch (error) {
      handleError(error, { taskId }, { customMessage: 'get task status failed' });
      throw error;
    }
  },

  getAria2Config: async () => {
    try {
      return await api.aria2.config();
    } catch (error) {
      handleError(error, {}, { customMessage: 'get aria2 config failed' });
      throw error;
    }
  },

  isFirstRun: async () => {
    try {
      return await api.settings.isFirstRun();
    } catch { return false; }
  },

  startAria2: async () => {
    try {
      await api.aria2.start();
    } catch (error) {
      handleError(error, {}, { customMessage: 'start aria2 failed' });
      throw error;
    }
  },

  getTaskResults: async (taskId) => {
    try {
      return await api.task.results(taskId);
    } catch (error) {
      handleError(error, { taskId }, { customMessage: 'get task results failed' });
      throw error;
    }
  },

  getClipboardText: async () => {
    try {
      return await api.system.clipboard();
    } catch (error) {
      handleError(error, {}, { customMessage: 'get clipboard failed' });
      throw error;
    }
  },

  readConfigFile: async (filePath) => {
    try {
      return await api.file.readConfig(filePath);
    } catch (error) {
      handleError(error, { filePath }, { customMessage: 'read config failed' });
      throw error;
    }
  },

  getAria2ConfigPath: async (taskId) => {
    try {
      return await api.aria2.configPath(taskId);
    } catch (error) {
      handleError(error, { taskId }, { customMessage: 'get config path failed' });
      throw error;
    }
  },

  checkFileExists: async (filePath) => {
    try {
      return await api.file.checkExists(filePath);
    } catch { return false; }
  },

  openFolder: async (folderPath) => {
    try {
      return await api.file.openFolder(folderPath);
    } catch { return false; }
  },

  cookieLogin: async () => {
    try {
      logger.api.request('cookie login', {});
      const result = await api.system.cookieLogin();
      logger.api.response('cookie login', { success: result.success });
      return result;
    } catch (error) {
      handleError(error, {}, { customMessage: 'cookie login failed' });
      throw error;
    }
  },

  findLocalFile: async (workId) => {
    try {
      return await api.file.findLocal(workId);
    } catch {
      return { found: false, video_path: null, images: null };
    }
  },

  getMediaUrl: (filePath) => api.file.getMediaUrl(filePath),

  crawlComments: async (awemeId, maxCount = 500) => {
    return api.comment.crawl(awemeId, maxCount);
  },

  /** 使用浏览器自动化爬取评论（API方式的备用方案） */
  crawlCommentsBrowser: async (awemeId: string, videoUrl?: string, maxCount = 500) => {
    try {
      logger.api.request('crawl comments browser', { awemeId, videoUrl, maxCount });
      const result = await api.comment.crawlBrowser(awemeId, videoUrl, maxCount);
      logger.api.response('crawl comments browser', { total: result.total });
      return result;
    } catch (error) {
      handleError(error, { awemeId, videoUrl, maxCount }, { customMessage: '浏览器爬取评论失败' });
      throw error;
    }
  },

  /** 分析评论数据并生成报告 */
  analyzeComments: async (csvFile?: string, generateReport = true) => {
    try {
      logger.api.request('analyze comments', { csvFile, generateReport });
      const result = await api.comment.analyze(csvFile, generateReport);
      logger.api.response('analyze comments', { hasHtml: !!result.html_report, hasWordcloud: !!result.wordcloud });
      return result;
    } catch (error) {
      handleError(error, { csvFile, generateReport }, { customMessage: '评论分析失败' });
      throw error;
    }
  },

  /** 使用 Spark 预处理评论数据 */
  preprocessComments: async (csvFile?: string) => {
    try {
      logger.api.request('preprocess comments', { csvFile });
      const result = await api.comment.preprocess(csvFile);
      logger.api.response('preprocess comments', { success: result.success, total: result.total_records });
      return result;
    } catch (error) {
      handleError(error, { csvFile }, { customMessage: '评论预处理失败' });
      throw error;
    }
  },

  /** 获取最新的分析报告 */
  getAnalysisReport: async (reportType: 'html' | 'wordcloud' = 'html') => {
    try {
      return await api.comment.getAnalysisReport(reportType);
    } catch (error) {
      handleError(error, { reportType }, { customMessage: '获取分析报告失败' });
      throw error;
    }
  },
};

export default bridge;
