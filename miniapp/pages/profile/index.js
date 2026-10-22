const app=getApp(); Page({data:{session:null},onShow(){this.setData({session:app.globalData.session});},logout(){app.clearSession();wx.reLaunch({url:'/pages/login/index'});}});
