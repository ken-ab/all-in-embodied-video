(() => {
  'use strict';
  const config=window.PREVIEW_CONFIG||{};
  const $=id=>document.getElementById(id);
  const video=$('sourceVideo');
  const names={douyin:'抖音',wechat:'微信视频号',xhs:'小红书'};
  const devices={iphone:{w:390,h:844,notch:true},android:{w:412,h:915,notch:false},small:{w:375,h:667,notch:false}};
  const canvases=Object.fromEntries(Object.keys(names).map(k=>[k,$('canvas-'+k)]));
  const state={platform:'douyin',device:'iphone',compare:false,chrome:true,expanded:false,safe:false,fit:'cover',cover:false,ready:false};
  const cover=new Image();const poster=new Image();let localUrl=null;
  const time=t=>{t=Math.max(0,Math.floor(Number(t)||0));return `${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;};
  const status=text=>{$('status').textContent=text;};
  const rr=(c,x,y,w,h,r=8)=>{c.beginPath();c.roundRect(x,y,w,h,r);};
  function text(c,value,x,y,size=14,color='#fff',weight=500,align='left'){
    c.fillStyle=color;c.font=`${weight} ${size}px "Segoe UI","Microsoft YaHei",sans-serif`;c.textAlign=align;c.textBaseline='alphabetic';c.fillText(value,x,y);
  }
  function lines(c,value,width,size){
    c.font=`500 ${size}px "Segoe UI","Microsoft YaHei",sans-serif`;
    const out=[];let row='';
    for(const ch of String(value)){if(ch==='\n'){out.push(row);row='';continue;}if(c.measureText(row+ch).width>width&&row){out.push(row);row=ch;}else row+=ch;}
    if(row)out.push(row);return out;
  }
  function icon(c,name,x,y,size=25,fill=false,color='#fff'){
    c.save();c.translate(x,y);c.scale(size/24,size/24);c.lineWidth=1.65;c.strokeStyle=color;c.fillStyle=color;c.lineCap='round';c.lineJoin='round';c.beginPath();
    if(name==='heart'){c.moveTo(12,21);c.bezierCurveTo(1,14,-2,7,3,4);c.bezierCurveTo(7,1,11,4,12,6);c.bezierCurveTo(14,2,19,1,22,5);c.bezierCurveTo(27,12,17,18,12,21);}
    else if(name==='comment'){c.roundRect(2,3,20,15,5);c.moveTo(7,18);c.lineTo(6,22);c.lineTo(12,18);}
    else if(name==='star'){for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,r=i%2?5:11;const px=12+Math.cos(a)*r,py=12+Math.sin(a)*r;i?c.lineTo(px,py):c.moveTo(px,py);}c.closePath();}
    else if(name==='share'){c.moveTo(2,20);c.quadraticCurveTo(2,9,14,8);c.lineTo(14,2);c.lineTo(23,11);c.lineTo(14,19);c.lineTo(14,13);c.quadraticCurveTo(6,13,2,20);c.closePath();}
    else if(name==='back'){c.moveTo(15,3);c.lineTo(6,12);c.lineTo(15,21);}
    else if(name==='search'){c.arc(10,10,7,0,Math.PI*2);c.moveTo(15,15);c.lineTo(22,22);}
    else if(name==='home'){c.moveTo(1,10);c.lineTo(12,1);c.lineTo(23,10);c.moveTo(4,9);c.lineTo(4,22);c.lineTo(9,22);c.lineTo(9,14);c.lineTo(15,14);c.lineTo(15,22);c.lineTo(20,22);c.lineTo(20,9);}
    else if(name==='menu'){[5,12,19].forEach(py=>{c.moveTo(3,py);c.lineTo(21,py);});}
    else if(name==='dots'){[4,12,20].forEach(px=>{c.moveTo(px+1,12);c.arc(px,12,1,0,Math.PI*2);});}
    if(fill)c.fill();else c.stroke();c.restore();
  }
  function avatar(c,x,y,r){c.fillStyle='#303a33';c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();c.strokeStyle='#fff';c.lineWidth=1.2;c.stroke();text(c,'具',x,y+5,Math.max(10,r*.65),'#fff',650,'center');}
  function phoneStatus(c,w,notch){
    text(c,'09:41',23,29,14,'#fff',650);c.fillStyle='#050505';if(notch){rr(c,w/2-51,7,102,29,16);c.fill();}else{c.beginPath();c.arc(w/2,17,5,0,Math.PI*2);c.fill();}
    const bx=w-42;c.strokeStyle='#fff';c.lineWidth=1.2;rr(c,bx,18,23,10,2);c.stroke();c.fillStyle='#fff';c.fillRect(bx+2,20,15,6);c.fillRect(bx+24,21,2,4);
    for(let i=0;i<4;i++)c.fillRect(w-85+i*4,26-i*2,2.5,3+i*2);
    c.beginPath();c.arc(w-53,24,7,Math.PI*1.19,Math.PI*1.81);c.stroke();
  }
  function videoRect(w,h,platform){return {x:0,y:0,w,h:h-(platform==='wechat'?65:platform==='xhs'?60:64)};}
  function drawMedia(c,source,r,fit){
    c.fillStyle='#060a09';c.fillRect(r.x,r.y,r.w,r.h);
    const sw=source.videoWidth||source.naturalWidth,sh=source.videoHeight||source.naturalHeight;if(!sw||!sh)return;
    const ratio=fit==='contain'?Math.min(r.w/sw,r.h/sh):Math.max(r.w/sw,r.h/sh);const dw=sw*ratio,dh=sh*ratio;
    c.save();c.beginPath();c.rect(r.x,r.y,r.w,r.h);c.clip();c.drawImage(source,r.x+(r.w-dw)/2,r.y+(r.h-dh)/2,dw,dh);c.restore();
  }
  function metadata(c,w,h,platform){
    const bottom=platform==='xhs'?h-103:h-108;const author=(config.authors||{})[platform]||'All In 具身';
    const grad=c.createLinearGradient(0,h-225,0,h-55);grad.addColorStop(0,'#0000');grad.addColorStop(1,'#0009');c.fillStyle=grad;c.fillRect(0,h-225,w,170);
    let y=bottom;
    if(platform==='xhs'){avatar(c,26,y-39,13);text(c,author,47,y-34,14,'#fff',600);text(c,time(video.duration||config.duration),w-18,y-34,12,'#eee',400,'right');}
    else{text(c,platform==='douyin'?'@'+author:author,15,y-40,16,'#fff',650);}
    const rows=lines(c,config.title||'本期视频标题',w-(platform==='douyin'?84:36),14);
    rows.slice(0,2).forEach((l,i)=>text(c,l+(i===1&&rows.length>2?'…':''),15,y-12+i*21,14,'#fff',450));
    if(platform!=='douyin')text(c,(config.description||'#具身智能 #学习记录').slice(0,34)+'　展开',15,y+28,12,'#ddd',400);
  }
  function chrome(c,w,h,p){
    phoneStatus(c,w,devices[state.device].notch);
    if(p==='douyin'){
      text(c,'热点　经验　直播　商城　关注',w/2-19,72,15,'#fffd',500,'center');text(c,'推荐',w-57,72,16,'#fff',700,'center');icon(c,'menu',14,53,21);icon(c,'search',w-30,52,21);
      const x=w-31;avatar(c,x,h-405,19);[{n:'heart',t:'赞'},{n:'comment',t:'评论'},{n:'star',t:'收藏'},{n:'share',t:'分享'}].forEach((a,i)=>{icon(c,a.n,x-13,h-361+i*63,27,true);text(c,a.t,x,h-321+i*63,11,'#fff',500,'center');});
      c.fillStyle='#111';c.fillRect(0,h-64,w,64);['首页','朋友','＋','消息','我'].forEach((l,i)=>text(c,l,(i+.5)*w/5,h-25,i===2?29:14,i===0?'#fff':'#999',i===0?650:500,'center'));
      metadata(c,w,h,p);
    }else if(p==='wechat'){
      icon(c,'back',17,53,21);text(c,'朋友　关注　推荐',w/2,72,17,'#fff',650,'center');icon(c,'search',w-37,53,21);
      const x=w-29;[{n:'share',t:'转发'},{n:'heart',t:'赞'},{n:'comment',t:'评论'}].forEach((a,i)=>{icon(c,a.n,x-12,h-312+i*61,25,true);text(c,a.t,x,h-273+i*61,11,'#fff',500,'center');});
      c.fillStyle='#101311';c.fillRect(0,h-65,w,65);text(c,'说点什么…',19,h-27,13,'#aaa',400);icon(c,'heart',w-124,h-43,23);icon(c,'comment',w-76,h-43,23);icon(c,'dots',w-36,h-43,21);
      metadata(c,w,h,p);
    }else{
      icon(c,'back',17,52,22);icon(c,'share',w-42,51,22);metadata(c,w,h,p);
      c.fillStyle='#111';c.fillRect(0,h-60,w,60);text(c,'说点什么…',18,h-25,13,'#aaa',400);icon(c,'heart',w-162,h-42,25);text(c,'赞',w-132,h-23,12);icon(c,'star',w-108,h-42,25);text(c,'收藏',w-80,h-23,12);icon(c,'comment',w-47,h-42,25);
    }
    const r=videoRect(w,h,p);const progress=Math.min(1,video.currentTime/(video.duration||config.duration||1));c.fillStyle='#ffffff45';c.fillRect(11,r.h-4,w-22,2);c.fillStyle='#fff';c.fillRect(11,r.h-4,(w-22)*progress,2);
    c.fillStyle='#fff';rr(c,w/2-54,h-8,108,4,3);c.fill();
  }
  function expanded(c,w,h){
    c.fillStyle='#0008';c.fillRect(0,0,w,h);const top=h*.49;c.fillStyle='#151816';rr(c,0,top,w,h-top,17);c.fill();text(c,'发布文案 · 展开示意',20,top+36,15,'#fff',650);
    const rows=lines(c,(config.title||'')+'\n\n'+(config.description||'本期发布文案')+'\n\n#具身智能 #学习记录',w-42,14);
    rows.slice(0,Math.floor((h-top-70)/23)).forEach((l,i)=>text(c,l,20,top+70+i*23,14,'#eee',450));
  }
  function safe(c,w,h,p){
    const r=videoRect(w,h,p);const x=w*.095,y=102,right=p==='xhs'?w-20:w-59,bottom=r.h-(p==='xhs'?132:142);
    c.fillStyle='#37ddae15';c.fillRect(x,y,right-x,bottom-y);c.save();c.strokeStyle='#65e5bb';c.lineWidth=1.2;c.setLineDash([5,4]);c.strokeRect(x,y,right-x,bottom-y);c.restore();
    c.fillStyle='#11251d';rr(c,x+5,y+7,105,22,4);c.fill();text(c,'参考内容安全区',x+12,y+22,10,'#a8f1d3',550);
  }
  function renderPhone(canvas,p){
    const {w,h}=devices[state.device],dpr=2;if(canvas.width!==w*dpr||canvas.height!==h*dpr){canvas.width=w*dpr;canvas.height=h*dpr;}
    const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
    const source=state.cover&&cover.complete&&cover.naturalWidth?cover:state.ready?video:poster;
    drawMedia(c,source,videoRect(w,h,p),state.cover?'contain':state.fit);
    if(state.chrome)chrome(c,w,h,p);if(state.chrome&&state.expanded)expanded(c,w,h);if(state.safe)safe(c,w,h,p);
  }
  function draw(){Object.entries(canvases).forEach(([p,canvas])=>renderPhone(canvas,p));$('timeReadout').textContent=`${time(video.currentTime)} / ${time(video.duration||config.duration)}`;$('timeline').value=video.currentTime||0;}
  function layout(){
    document.querySelectorAll('[data-phone]').forEach(el=>{el.hidden=!state.compare&&el.dataset.phone!==state.platform;});
    $('phoneGrid').classList.toggle('comparing',state.compare);$('stageTitle').textContent=state.compare?'三平台 · 同一视频，同一帧':names[state.platform]+' · 观看界面';
    document.querySelectorAll('[data-platform]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.platform===state.platform)));
    const {w,h}=devices[state.device],height=Math.max(420,Math.min(720,window.innerHeight-285));const width=Math.round(height*w/h);
    $('phoneGrid').style.setProperty('--phone-width',Math.min(width,window.innerWidth-42)+'px');$('phoneGrid').style.setProperty('--device-width',w+'px');draw();
  }
  async function playPause(){if(!state.ready)return;if(state.cover){state.cover=false;$('coverMode').checked=false;}if(video.paused){try{await video.play();}catch{status('请点击播放，或重新选择视频');}}else video.pause();}
  function seek(t){if(!Number.isFinite(t)||!state.ready)return;const target=Math.max(0,Math.min((video.duration||1)-.05,t));if(Math.abs(video.currentTime-target)<.001){draw();return;}$('exportButton').disabled=true;status('正在定位 '+time(target));video.currentTime=target;draw();}
  document.querySelectorAll('[data-platform]').forEach(b=>b.addEventListener('click',()=>{state.platform=b.dataset.platform;layout();}));
  $('compare').addEventListener('change',e=>{state.compare=e.target.checked;layout();});
  $('device').addEventListener('change',e=>{state.device=e.target.value;layout();});
  $('fit').addEventListener('change',e=>{state.fit=e.target.value;draw();});
  $('zoom').addEventListener('change',e=>{$('phoneGrid').classList.toggle('actual-size',e.target.value==='actual');document.body.classList.toggle('actual-size',e.target.value==='actual');layout();});
  for(const [id,key] of [['chrome','chrome'],['expanded','expanded'],['safe','safe'],['coverMode','cover']])$(id).addEventListener('change',e=>{state[key]=e.target.checked;if(key==='cover'&&state.cover)video.pause();draw();});
  $('playButton').addEventListener('click',playPause);Object.values(canvases).forEach(c=>c.addEventListener('click',playPause));
  $('backButton').addEventListener('click',()=>seek(video.currentTime-5));$('nextButton').addEventListener('click',()=>seek(video.currentTime+5));
  $('timeline').addEventListener('input',e=>seek(Number(e.target.value)));$('muted').addEventListener('change',e=>{video.muted=e.target.checked;});
  $('jumpForm').addEventListener('submit',e=>{e.preventDefault();const v=$('jumpTime').value.trim();if(!/^\d+(?::[0-5]?\d){0,2}(?:\.\d+)?$/.test(v)){status('时间格式：08:30 或秒数');return;}seek(v.split(':').reduce((a,n)=>a*60+Number(n),0));});
  function setCheckpoints(checks){$('checkpoints').textContent='';checks.forEach(item=>{const b=document.createElement('button');b.textContent=`${item.label} ${time(item.time)}`;b.addEventListener('click',()=>{video.pause();seek(Number(item.time));});$('checkpoints').append(b);});}
  setCheckpoints(config.checkpoints||[{label:'开头',time:2},{label:'中段',time:(config.duration||1)/2},{label:'结尾',time:Math.max(0,(config.duration||5)-5)}]);
  $('fileInput').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;if(localUrl)URL.revokeObjectURL(localUrl);localUrl=URL.createObjectURL(f);state.ready=false;state.cover=false;$('coverMode').checked=false;$('coverMode').disabled=true;config.title=f.name.replace(/\.[^.]+$/,'');config.description='本地视频预览';config.initial_time=2;video.src=localUrl;video.load();$('assetTitle').textContent=config.title;$('downloadVideo').href=localUrl;status('正在读取本地视频');});
  $('exportButton').addEventListener('click',async()=>{
    if(video.seeking){status('请等待定位完成后保存');return;}if(!state.ready&&!state.cover){status('请等待视频就绪');return;}video.pause();draw();
    const selected=state.compare?Object.keys(names):[state.platform];const gap=28,pad=28;const phoneW=devices[state.device].w*2,phoneH=devices[state.device].h*2;
    const out=document.createElement('canvas');out.width=selected.length*phoneW+(selected.length-1)*gap+pad*2;out.height=phoneH+144;const c=out.getContext('2d');c.fillStyle='#eef1e9';c.fillRect(0,0,out.width,out.height);
    selected.forEach((p,i)=>{const x=pad+i*(phoneW+gap);text(c,names[p]+' · '+time(video.currentTime),x,40,23,'#21442f',650);c.drawImage(canvases[p],x,60);});
    text(c,'本地模拟 · 非发布截图 · 界面随机型、App版本与文案变化',pad,out.height-25,18,'#60705f',450);
    try{
      const png=out.toDataURL('image/png');
      if(location.protocol==='http:'&&location.hostname==='127.0.0.1'){
        $('exportButton').disabled=true;status('正在保存检查图');
        const response=await fetch('snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:png})});
        if(!response.ok)throw new Error('保存失败');const saved=await response.json();
        $('savedImage').href=saved.url;$('savedImage').hidden=false;status('已保存到本期“手机预览/检查图”');
      }else{const link=document.createElement('a');link.href=png;link.download=`${config.id||'video'}_${time(video.currentTime).replace(':','-')}_模拟预览.png`;link.click();status('检查图已导出');}
    }catch{status('保存失败，请使用“启动手机预览”打开网页');}finally{$('exportButton').disabled=false;}
  });
  video.addEventListener('loadedmetadata',()=>{$('timeline').max=video.duration;$('assetSpec').textContent=`${video.videoWidth} × ${video.videoHeight} · ${time(video.duration)}`;if(localUrl)setCheckpoints([{label:'开头',time:Math.min(2,video.duration/2)},{label:'中段',time:video.duration/2},{label:'结尾',time:Math.max(0,video.duration-5)}]);});
  video.addEventListener('loadeddata',()=>{state.ready=true;seek(Math.min(config.initial_time||2,Math.max(0,video.duration-.1)));status('视频已就绪');draw();});
  video.addEventListener('seeking',()=>{$('exportButton').disabled=true;});
  video.addEventListener('seeked',()=>{$('exportButton').disabled=false;status('已定位 '+time(video.currentTime));draw();});video.addEventListener('timeupdate',draw);
  video.addEventListener('play',()=>{$('playButton').textContent='Ⅱ';$('playButton').setAttribute('aria-label','暂停');status('正在播放');});
  video.addEventListener('pause',()=>{$('playButton').textContent='▶';$('playButton').setAttribute('aria-label','播放');draw();});
  video.addEventListener('error',()=>{state.ready=false;status('视频未能加载，请选择本地MP4或使用启动脚本');});
  function animate(){if(!video.paused&&state.ready)draw();requestAnimationFrame(animate);}requestAnimationFrame(animate);
  cover.onload=draw;poster.onload=draw;if(config.cover)cover.src=config.cover;else $('coverMode').disabled=true;if(config.poster)poster.src=config.poster;
  $('assetTitle').textContent=config.title||'本期成片';$('assetSpec').textContent=`${config.width||1080} × ${config.height||1920} · ${time(config.duration)}`;
  $('footerTime').textContent='生成于 '+(config.built_at||'本机');
  $('downloadVideo').href=config.video||'video.mp4';
  video.src=config.video||'video.mp4';video.load();window.addEventListener('resize',layout);layout();
})();
