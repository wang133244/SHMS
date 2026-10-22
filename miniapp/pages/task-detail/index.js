const {request,upload}=require('../../services/request');
Page({
  data:{task:null,note:'',photos:[],changeReason:'',uploading:false},
  onLoad(options){this.taskId=options.id;this.load();},
  load(){request(`/tasks/${this.taskId}`).then(task=>this.setData({task})).catch(()=>wx.showToast({title:'任务无法加载',icon:'none'}));},
  inputNote(e){this.setData({note:e.detail.value});},
  inputReason(e){this.setData({changeReason:e.detail.value});},
  choosePhotos(){
    const remaining=3-this.data.photos.length;if(remaining<=0){wx.showToast({title:'最多上传 3 张照片',icon:'none'});return;}
    wx.chooseMedia({count:remaining,mediaType:['image'],sourceType:['camera','album'],success:async result=>{
      this.setData({uploading:true});
      try{const uploaded=[];for(const item of result.tempFiles){uploaded.push(await upload('/tasks/uploads',item.tempFilePath));}this.setData({photos:[...this.data.photos,...uploaded.map(item=>item.key)]});}
      catch(error){wx.showToast({title:'照片上传失败',icon:'none'});}
      finally{this.setData({uploading:false});}
    }});
  },
  async submit(){
    try{await request(`/tasks/${this.taskId}/submissions`,{method:'POST',data:{note:this.data.note,photo_keys:this.data.photos}});wx.showToast({title:'已提交'});this.load();}
    catch(error){wx.showToast({title:error.detail||'提交失败',icon:'none'});}
  },
  async requestChange(){
    if(!this.data.changeReason.trim()){wx.showToast({title:'请填写更改原因',icon:'none'});return;}
    try{await request(`/tasks/${this.taskId}/change-requests`,{method:'POST',data:{reason:this.data.changeReason}});wx.showToast({title:'申请已提交'});this.load();}
    catch(error){wx.showToast({title:error.detail||'申请失败',icon:'none'});}
  },
});
