const app = getApp();
const { request } = require('../../services/request');

const POSITION_LABELS = {
  logistics: '后勤', health: '保健', care: '保育', kitchen: '厨房', business: '业务人员', security: '保安',
};

function roleActions(session, positionLabel) {
  if (session.role === 'admin') {
    return [
      { icon: '园', title: '园务管理', desc: '查看园务数据与待办审核', url: '/pages/admin/index' },
      { icon: '人', title: '员工账号', desc: '维护岗位、账号与登录信息', url: '/pages/admin/index' },
      { icon: '任', title: '任务模板', desc: '管理岗位职责和任务规则', url: '/pages/admin/index' },
      { icon: '审', title: '审核记录', desc: '处理员工修改申请与知识发布', url: '/pages/admin/index' },
    ];
  }
  return [
    { icon: '今', title: '今日任务', desc: `${positionLabel || '岗位'}的今日工作安排`, url: '/pages/tasks/index' },
    { icon: '问', title: '岗位问答', desc: '查询岗位职责和工作要点', url: '/pages/chat/index' },
    { icon: '岗', title: '岗位工作台', desc: '查看任务详情并提交完成记录', url: '/pages/tasks/index' },
    { icon: '我', title: '我的账号', desc: '查看个人岗位和登录信息', url: '/pages/profile/index' },
  ];
}

Page({
  data: { session: null, tasks: [], pendingAssignment: false, roleLabel: '', positionLabel: '', displayEmployeeNo: '', quickActions: [] },
  onShow() {
    const session = app.globalData.session;
    if (!session) { wx.reLaunch({ url: '/pages/login/index' }); return; }
    const pendingAssignment = session.status === 'pending_assignment';
    const positionLabel = POSITION_LABELS[session.position] || '待分配岗位';
    const roleLabel = session.role === 'admin' ? '园务管理员' : positionLabel;
    const displayEmployeeNo = session.login_employee_no || session.employee_no;
    this.setData({ session, pendingAssignment, roleLabel, positionLabel, displayEmployeeNo, quickActions: roleActions(session, positionLabel), tasks: [] });
    if (session.role === 'employee' && !pendingAssignment) {
      request('/tasks/today').then(tasks => this.setData({ tasks })).catch(() => {});
    }
  },
  go(event) { wx.navigateTo({ url: event.currentTarget.dataset.url }); },
  logout() { app.clearSession(); wx.reLaunch({ url: '/pages/login/index' }); },
});
