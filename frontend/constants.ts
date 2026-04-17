/**
 * 应用常量配置
 * 统一管理项目中使用的常量，避免重复定义
 */

/**
 * 应用默认设置
 */
export const APP_DEFAULTS = {
  COOKIE: '',
  USER_AGENT: '',
  ENABLE_INCREMENTAL_FETCH: true, // 默认启用增量采集
} as const;

/**
 * 路径相关常量
 */
export const PATHS = {
  CONFIG_DIR: 'config',
  SETTINGS_FILE: 'settings.json',
} as const;
