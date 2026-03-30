(function() {
  'use strict';
  
  const SERVER_URL = 'http://localhost:8000/api/system/receive-cookie';
  
  function extractCookie() {
    return document.cookie;
  }
  
  function getUserAgent() {
    return navigator.userAgent;
  }
  
  async function sendCookieToServer() {
    const cookie = extractCookie();
    const userAgent = getUserAgent();
    
    if (!cookie) {
      console.log('[抖音Cookie助手] 未检测到Cookie，请先登录');
      return { success: false, error: '未检测到Cookie，请先登录' };
    }
    
    try {
      const response = await fetch(SERVER_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cookie: cookie,
          user_agent: userAgent,
          source: 'douyin_cookie_helper'
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        console.log('[抖音Cookie助手] Cookie已成功发送到应用');
        showNotification('Cookie获取成功！请返回应用查看', 'success');
      } else {
        console.log('[抖音Cookie助手] 发送失败:', result.error);
        showNotification('发送失败: ' + result.error, 'error');
      }
      
      return result;
    } catch (error) {
      console.error('[抖音Cookie助手] 发送失败:', error);
      showNotification('发送失败，请确保应用正在运行', 'error');
      return { success: false, error: error.message };
    }
  }
  
  function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 8px;
      color: white;
      font-size: 14px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      z-index: 999999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: opacity 0.3s;
      ${type === 'success' ? 'background: #10b981;' : 'background: #ef4444;'}
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }
  
  window.douyinCookieHelper = {
    sendCookie: sendCookieToServer,
    extractCookie: extractCookie
  };
  
  console.log('[抖音Cookie助手] 扩展已加载，调用 douyinCookieHelper.sendCookie() 发送Cookie');
  
})();
