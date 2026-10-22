const {request}=require('../../services/request');
Page({data:{question:'',answer:'',citations:[]},input(e){this.setData({question:e.detail.value});},ask(){request('/chat/ask',{method:'POST',data:{question:this.data.question}}).then(data=>this.setData(data)).catch(()=>wx.showToast({title:'问答暂不可用',icon:'none'}));}});
