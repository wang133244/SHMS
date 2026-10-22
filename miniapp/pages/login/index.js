const app = getApp();
const { request } = require('../../services/request');

Page({
  data: {
    employeeNo: '', password: '', busy: false, error: '',
    demoAccounts: [
      { employeeNo: '0001', label: '管理员' },
      { employeeNo: '1001', label: '后勤' },
      { employeeNo: '2001', label: '保健' },
      { employeeNo: '3001', label: '保育' },
      { employeeNo: '4001', label: '厨房' },
      { employeeNo: '5001', label: '业务' },
    ],
  },
  inputEmployeeNo(event) { this.setData({ employeeNo: event.detail.value, error: '' }); },
  inputPassword(event) { this.setData({ password: event.detail.value, error: '' }); },
  selectDemoAccount(event) {
    const account = this.data.demoAccounts[Number(event.currentTarget.dataset.index)];
    if (!account) return;
    this.setData({ employeeNo: account.employeeNo, password: '123456', error: '' });
  },
  async passwordLogin() {
    const employeeNo = this.data.employeeNo.trim();
    const password = this.data.password;
    if (!employeeNo || !password) {
      this.setData({ error: '请输入工号和密码' });
      return;
    }
    this.setData({ busy: true, error: '' });
    try {
      const session = await request('/auth/password-login', {
        method: 'POST',
        data: { employee_no: employeeNo, password },
      });
      app.setSession(session);
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ error: (error && (error.detail || error.message)) || '工号或密码错误，请重试' });
    } finally {
      this.setData({ busy: false });
    }
  },
  async phoneLogin(event) {
    const phoneCode = event.detail.code;
    if (!phoneCode) {
      wx.showToast({ title: '需要授权手机号', icon: 'none' });
      return;
    }
    wx.login({ success: async result => {
      try {
        const session = await request('/auth/wechat/login', {
          method: 'POST',
          data: { login_code: result.code, phone_code: phoneCode },
        });
        if (session.status === 'pending_binding') {
          wx.showModal({ title: '账号待绑定', content: '请联系管理员创建员工账号后再登录。', showCancel: false });
          return;
        }
        app.setSession(session);
        wx.reLaunch({ url: '/pages/home/index' });
      } catch (_) {
        wx.showToast({ title: '微信登录失败', icon: 'none' });
      }
    }, fail: () => wx.showToast({ title: '微信登录失败', icon: 'none' }) });
  },
});
