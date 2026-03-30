chrome.runtime.onInstalled.addListener(() => {
  console.log('抖音Cookie助手已安装');
});

chrome.action.onClicked.addListener((tab) => {
  if (tab.url && tab.url.includes('douyin.com')) {
    chrome.tabs.sendMessage(tab.id, { action: 'extractCookie' });
  }
});
