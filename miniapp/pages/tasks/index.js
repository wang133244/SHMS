const {request}=require('../../services/request');
Page({
  data:{tasks:[],error:''},
  onShow(){request('/tasks/today').then(tasks=>this.setData({tasks,error:''})).catch(()=>this.setData({error:'任务暂时无法加载'}));},
  openTask(e){wx.navigateTo({url:`/pages/task-detail/index?id=${e.currentTarget.dataset.id}`});},
});
