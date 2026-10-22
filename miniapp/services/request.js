const app = getApp();
function request(path, options = {}) {
  const token = app.globalData.session && app.globalData.session.access_token;
  return new Promise((resolve, reject) => wx.request({
    url: `${app.globalData.apiBase}${path}`, method: options.method || 'GET', data: options.data,
    header: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    success(response) { if (response.statusCode === 401) { app.clearSession(); wx.reLaunch({url:'/pages/login/index'}); } response.statusCode < 300 ? resolve(response.data) : reject(response.data); },
    fail: reject,
  }));
}
function upload(path, filePath, name = 'file') {
  const token = app.globalData.session && app.globalData.session.access_token;
  return new Promise((resolve, reject) => wx.uploadFile({
    url: `${app.globalData.apiBase}${path}`, filePath, name,
    header: token ? { Authorization: `Bearer ${token}` } : {},
    success(response) {
      let data;
      try { data = JSON.parse(response.data); } catch (error) { reject(error); return; }
      response.statusCode < 300 ? resolve(data) : reject(data);
    },
    fail: reject,
  }));
}
module.exports = { request, upload };
