document.addEventListener('DOMContentLoaded', function() {
  const extractBtn = document.getElementById('extractBtn');
  const statusDiv = document.getElementById('status');
  
  function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
  }
  
  extractBtn.addEventListener('click', async function() {
    extractBtn.disabled = true;
    showStatus('正在提取Cookie...', 'loading');
    
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      if (!tab.url || !tab.url.includes('douyin.com')) {
        showStatus('请先打开抖音网站 (douyin.com)', 'error');
        extractBtn.disabled = false;
        return;
      }
      
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          if (window.douyinCookieHelper) {
            return window.douyinCookieHelper.extractCookie();
          }
          return document.cookie;
        }
      });
      
      const cookie = results[0].result;
      
      if (!cookie) {
        showStatus('未检测到Cookie，请先登录抖音', 'error');
        extractBtn.disabled = false;
        return;
      }
      
      const response = await fetch('http://localhost:8000/api/system/receive-cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookie: cookie,
          user_agent: navigator.userAgent,
          source: 'douyin_cookie_helper'
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        showStatus('✓ Cookie已发送到应用！', 'success');
      } else {
        showStatus('发送失败: ' + result.error, 'error');
      }
      
    } catch (error) {
      showStatus('发送失败: ' + error.message, 'error');
    }
    
    extractBtn.disabled = false;
  });
});
