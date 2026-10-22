const { request, upload } = require('../../services/request');

const POSITIONS = ['后勤', '保安', '保健', '保育', '厨房', '业务人员'];
const POSITION_CODES = ['logistics', 'security', 'health', 'care', 'kitchen', 'business'];
const STAFF_POSITIONS = ['待分配', ...POSITIONS];
const FREQUENCIES = ['daily', 'weekly', 'monthly', 'semester', 'security_weekend'];
const CALENDAR_KINDS = ['workday', 'weekend', 'holiday', 'school_break', 'makeup_workday'];

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

Page({
  data: {
    tabs: ['概览', '修改审核', '员工', '模板与知识', '园历'], activeTab: 0,
    dashboard: {}, staff: [], requests: [], templates: [], drafts: null,
    positions: POSITIONS, positionIndex: 0, staffPositions: STAFF_POSITIONS, staffPositionIndex: 0, frequencies: FREQUENCIES, frequencyIndex: 0,
    calendarKinds: CALENDAR_KINDS, calendarKindIndex: 0, calendarDate: today(),
    editId: null, form: { title: '', time_range: '', due_time: '', content: '', acceptance_criteria: '', schedule_rule: '{}' },
    newStaff: { name: '', employee_no: '', phone: '', password: '' }, error: '', busy: false,
  },
  onShow() {
    const session = getApp().globalData.session;
    if (!session || session.role !== 'admin') {
      wx.showToast({ title: '仅管理员可访问', icon: 'none' });
      wx.navigateBack();
      return;
    }
    this.refresh();
  },
  onPullDownRefresh() { this.refresh().finally(() => wx.stopPullDownRefresh()); },
  refresh() {
    return Promise.all([this.loadDashboard(), this.loadRequests(), this.loadStaff(), this.loadTemplates()]);
  },
  fail(error) { this.setData({ error: (error && (error.detail || error.message)) || '操作失败，请检查网络后重试' }); },
  loadDashboard() { return request('/admin/dashboard').then(dashboard => this.setData({ dashboard })).catch(error => this.fail(error)); },
  loadRequests() { return request('/admin/change-requests').then(requests => this.setData({ requests })).catch(error => this.fail(error)); },
  loadStaff() { return request('/admin/staff').then(staff => this.setData({ staff })).catch(error => this.fail(error)); },
  loadTemplates() { return request('/admin/task-templates').then(templates => this.setData({ templates })).catch(error => this.fail(error)); },
  selectTab(event) { this.setData({ activeTab: Number(event.currentTarget.dataset.index), error: '' }); },
  input(event) {
    const field = event.currentTarget.dataset.field;
    const group = event.currentTarget.dataset.group || 'form';
    this.setData({ [`${group}.${field}`]: event.detail.value });
  },
  choosePosition(event) { this.setData({ positionIndex: Number(event.detail.value) }); },
  chooseStaffPosition(event) { this.setData({ staffPositionIndex: Number(event.detail.value) }); },
  chooseFrequency(event) { this.setData({ frequencyIndex: Number(event.detail.value) }); },
  chooseCalendarKind(event) { this.setData({ calendarKindIndex: Number(event.detail.value) }); },
  chooseCalendarDate(event) { this.setData({ calendarDate: event.detail.value }); },
  editTemplate(event) {
    const template = this.data.templates.find(item => item.id === Number(event.currentTarget.dataset.id));
    if (!template) return;
    const ruleText = JSON.stringify(template.schedule_rule || {}, null, 2);
    this.setData({
      editId: template.id,
      positionIndex: Math.max(0, POSITION_CODES.indexOf(template.position_code)),
      frequencyIndex: Math.max(0, FREQUENCIES.indexOf(template.frequency)),
      form: { title: template.title || '', time_range: template.time_range || '', due_time: template.due_time || '', content: template.content || '', acceptance_criteria: template.acceptance_criteria || '', schedule_rule: ruleText },
      error: '',
    });
  },
  resetTemplate() {
    this.setData({ editId: null, form: { title: '', time_range: '', due_time: '', content: '', acceptance_criteria: '', schedule_rule: '{}' }, error: '' });
  },
  saveTemplate() {
    const form = this.data.form;
    let scheduleRule;
    try { scheduleRule = JSON.parse(form.schedule_rule || '{}'); } catch (_) { this.setData({ error: '日期规则必须是有效 JSON' }); return; }
    const body = {
      position_code: POSITION_CODES[this.data.positionIndex], title: form.title,
      frequency: FREQUENCIES[this.data.frequencyIndex], schedule_rule: scheduleRule,
      time_range: form.time_range || null, due_time: form.due_time || null,
      content: form.content, acceptance_criteria: form.acceptance_criteria || null,
    };
    this.setData({ busy: true, error: '' });
    const action = this.data.editId
      ? request(`/admin/task-templates/${this.data.editId}`, { method: 'PATCH', data: body })
      : request('/admin/task-templates', { method: 'POST', data: body });
    action.then(() => { wx.showToast({ title: '草稿已保存' }); this.resetTemplate(); return this.loadTemplates(); })
      .catch(error => this.fail(error)).finally(() => this.setData({ busy: false }));
  },
  publishTemplate(event) {
    const id = event.currentTarget.dataset.id;
    request(`/admin/task-templates/${id}/publish`, { method: 'POST' })
      .then(() => { wx.showToast({ title: '模板已发布' }); this.loadTemplates(); this.loadDashboard(); })
      .catch(error => this.fail(error));
  },
  generateToday() {
    request(`/admin/tasks/generate?target_date=${today()}`, { method: 'POST' })
      .then(result => { wx.showToast({ title: `新增 ${result.created} 条任务` }); this.loadDashboard(); })
      .catch(error => this.fail(error));
  },
  review(event) {
    const id = event.currentTarget.dataset.id;
    const action = event.currentTarget.dataset.action;
    const send = reason => request(`/admin/change-requests/${id}/${action}`, {
      method: 'POST', data: action === 'reject' ? { reason } : {},
    });
    if (action === 'approve') {
      wx.showModal({ title: '同意修改申请？', content: '同意后该任务将重新开放，员工可重新提交。', success: result => {
        if (result.confirm) send('').then(() => { this.loadRequests(); this.loadDashboard(); }).catch(error => this.fail(error));
      } });
      return;
    }
    wx.showModal({ title: '拒绝原因', editable: true, placeholderText: '请填写拒绝原因', success: result => {
      if (!result.confirm) return;
      const reason = (result.content || '').trim();
      if (!reason) { this.setData({ error: '拒绝时必须填写原因' }); return; }
      send(reason).then(() => { this.loadRequests(); this.loadDashboard(); }).catch(error => this.fail(error));
    } });
  },
  createStaff() {
    const staff = this.data.newStaff;
    const positionIndex = this.data.staffPositionIndex;
    const body = { ...staff, position_code: positionIndex ? POSITION_CODES[positionIndex - 1] : null, role: 'employee' };
    request('/admin/staff', { method: 'POST', data: body })
      .then(() => { this.setData({ newStaff: { name: '', employee_no: '', phone: '', password: '' }, staffPositionIndex: 0 }); wx.showToast({ title: '员工已添加' }); this.loadStaff(); })
      .catch(error => this.fail(error));
  },
  assignPosition(event) {
    const staffId = Number(event.currentTarget.dataset.id);
    wx.showActionSheet({ itemList: POSITIONS, success: result => {
      request(`/admin/staff/${staffId}/position`, { method: 'PATCH', data: { position_code: POSITION_CODES[result.tapIndex] } })
        .then(() => { wx.showToast({ title: '岗位已分配' }); return this.loadStaff(); })
        .catch(error => this.fail(error));
    } });
  },
  uploadWorkbook() {
    wx.chooseMessageFile({ count: 1, type: 'file', extension: ['xlsx'], success: result => {
      const file = result.tempFiles[0];
      upload('/admin/knowledge-documents/import-excel', file.path)
        .then(document => request(`/admin/knowledge-documents/${document.id}/drafts`).then(drafts => {
          this.setData({ drafts: { ...drafts, file_name: document.file_name, document_id: document.id }, activeTab: 3 });
          this.loadTemplates();
        }))
        .catch(error => this.fail(error));
    } });
  },
  publishChunk(event) {
    request(`/admin/knowledge-chunks/${event.currentTarget.dataset.id}/publish`, { method: 'POST' })
      .then(() => { wx.showToast({ title: '知识已发布' }); this.loadDashboard(); this.openDrafts(this.data.drafts.document_id); })
      .catch(error => this.fail(error));
  },
  classifyChunk(event) {
    const id = event.currentTarget.dataset.id;
    wx.showActionSheet({ itemList: POSITIONS, success: result => {
      request(`/admin/knowledge-chunks/${id}`, { method: 'PATCH', data: { position_code: POSITION_CODES[result.tapIndex] } })
        .then(() => request(`/admin/knowledge-chunks/${id}/publish`, { method: 'POST' }))
        .then(() => { wx.showToast({ title: '已分类并发布' }); this.loadDashboard(); this.openDrafts(this.data.drafts.document_id); })
        .catch(error => this.fail(error));
    } });
  },
  publishDraftTemplate(event) { this.publishTemplate(event); },
  openDrafts(documentId) {
    request(`/admin/knowledge-documents/${documentId}/drafts`).then(drafts => this.setData({ drafts: { ...drafts, document_id: documentId, file_name: this.data.drafts && this.data.drafts.file_name } })).catch(error => this.fail(error));
  },
  saveCalendar() {
    const kind = CALENDAR_KINDS[this.data.calendarKindIndex];
    wx.showModal({ title: '设置园历类型', editable: true, placeholderText: '原因或备注（可选）', success: result => {
      if (!result.confirm) return;
      request(`/admin/calendar/${this.data.calendarDate}`, { method: 'PUT', data: { kind, reason: result.content || null } })
        .then(() => wx.showToast({ title: '园历已保存' })).catch(error => this.fail(error));
    } });
  },
});
