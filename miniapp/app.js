App({
  globalData: { apiBase: 'http://127.0.0.1:8000/api/v1', session: null },
  onLaunch() { this.globalData.session = wx.getStorageSync('session') || null; },
  setSession(session) { this.globalData.session = session; wx.setStorageSync('session', session); },
  clearSession() { this.globalData.session = null; wx.removeStorageSync('session'); },
});
