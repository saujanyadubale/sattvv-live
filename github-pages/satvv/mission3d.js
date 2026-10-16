/* SAT-V&V v0.9.9: dependency-free 3D projection for conceptual subsystem geometry.
 * This is a visualization of recorded simulator evidence, NOT flight CAD or an orbital dynamics model.
 * No hidden injected-fault information is used until the user explicitly reveals ground truth.
 */
'use strict';
(function () {
 const SYSTEMS=['EPS','THERMAL','OBC','COMMS','PAYLOAD','ADCS'];
 const HYP_TO_SYS={resistance_ramp:'EPS',intermittent_resistance:'EPS',sensor_drift:'THERMAL',heater_fault:'THERMAL',radio_burst:'COMMS',adcs_gyro_bias:'ADCS',adcs_wheel_weak:'ADCS',adcs_star_dropout:'ADCS'};
 const color={base:'#7b9db0',EPS:'#66dec3',THERMAL:'#f6b96e',OBC:'#d1dbf5',COMMS:'#7ab9ff',PAYLOAD:'#b5a6ff',ADCS:'#b2e7f4'};
 const FACE=[[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]];
 function boxFaces(cx,cy,cz,sx,sy,sz,id,finish,alpha=1){const x=sx/2,y=sy/2,z=sz/2;
  const v=[[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],[-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]].map(q=>[q[0]+cx,q[1]+cy,q[2]+cz]);
  return FACE.map((f,i)=>({id,verts:f.map(k=>v[k]),finish,face:i,alpha}));}
 class MissionView {
  constructor(canvas){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.yaw=-.46;this.pitch=-.30;this.zoom=1;this.stage=null;this.record=null;this.prior=[];this.truth=[];this.showTruth=false;this.follow=true;this.motion=!matchMedia('(prefers-reduced-motion: reduce)').matches;this.frame=0;this.drag=null;
   this.anchors={EPS:[-.75,.45,.75],THERMAL:[.72,.47,.78],OBC:[0,0,.94],COMMS:[1.6,.56,0],PAYLOAD:[0,-.88,.20],ADCS:[-.48,-.48,.88]};
   this.onPointerDown=e=>{this.drag={x:e.clientX,y:e.clientY,yaw:this.yaw,pitch:this.pitch};canvas.setPointerCapture(e.pointerId)};
   this.onPointerMove=e=>{if(!this.drag)return;this.yaw=this.drag.yaw+(e.clientX-this.drag.x)*.008;this.pitch=Math.min(1.1,Math.max(-1.1,this.drag.pitch+(e.clientY-this.drag.y)*.006));this.draw()};
   this.onPointerUp=()=>{this.drag=null};
   canvas.addEventListener('pointerdown',this.onPointerDown);canvas.addEventListener('pointermove',this.onPointerMove);canvas.addEventListener('pointerup',this.onPointerUp);canvas.addEventListener('pointercancel',this.onPointerUp);
   canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.7,Math.min(1.7,this.zoom-(e.deltaY>0?.08:-.08)));this.draw()},{passive:false});
   this.resizeObserver=typeof ResizeObserver!=='undefined'?new ResizeObserver(()=>this.draw()):null;
   this.resizeObserver?.observe(canvas);this.raf=0;this.animate=this.animate.bind(this);if(this.motion)this.raf=requestAnimationFrame(this.animate);this.draw();
  }
  set(record,prior){this.record=record||null;this.prior=prior||{};if(this.follow&&record?.status==='FAIL')this.zoom=Math.min(1.35,this.zoom+.05);this.draw()}
  setOracle(oracle,show){this.showTruth=!!show;this.truth=show?(oracle?.faults||[]):[];this.draw()}
  focus(system){this.stage=system;this.draw()}
  reset(){this.yaw=-.46;this.pitch=-.3;this.zoom=1;this.draw()}
  animate(t){if(!document.hidden&&this.canvas.getClientRects().length){this.frame=t/1000;this.draw()}this.raf=requestAnimationFrame(this.animate)}
  projection(v,w,h){const [x,y,z]=v;const c=Math.cos(this.yaw),s=Math.sin(this.yaw);const xr=x*c-z*s,depth=x*s+z*c;const cp=Math.cos(this.pitch),sp=Math.sin(this.pitch);const yr=y*cp-depth*sp,d=y*sp+depth*cp;const factor=1/(1+d*.07);const scale=Math.min(w*.12,h*.20)*this.zoom*factor;return{x:w*.39+xr*scale,y:h*.52-yr*scale,z:d}}
  draw(){const canvas=this.canvas,rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;const w=rect.width,h=rect.height,dpr=Math.min(2,devicePixelRatio||1);if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}const g=this.ctx;g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
    // Transparent fallback canvas shares the restrained CSS starfield with WebGL.
    // No decorative star is drawn on top of the spacecraft.
    g.strokeStyle='#244758';g.lineWidth=.7;g.globalAlpha=.17;for(let i=0;i<8;i++){const y=h*.79+i*i*1.9;g.beginPath();g.moveTo(0,y);g.lineTo(w,y);g.stroke()}g.globalAlpha=1;
    const p=(v)=>this.projection(v,w,h),active=this.stage||this.record?.subsystem;
    const faces=[];faces.push(...boxFaces(0,0,0,1.7,1.8,1.55,'base','#657f99'));
    // Two segmented blue solar arrays
    for(const side of [-1,1]){
      faces.push(...boxFaces(side*2.38,.08,0,2.6,.09,1.25,'EPS','#335875'));
      for(let u=0;u<5;u++)for(let v=0;v<2;v++){let xx=side*(1.25+.49*u),zz=-.34+.69*v;faces.push(...boxFaces(xx,.14,zz,.42,.016,.59,'EPS','#286386'));}
    }
    faces.push(...boxFaces(-.53,.45,.86,.58,.40,.30,'EPS','#398b84'));
    faces.push(...boxFaces(.49,.46,.87,.48,.43,.25,'THERMAL','#a76d4a'));
    faces.push(...boxFaces(.02,-.08,.94,.65,.56,.20,'OBC','#7191ad'));
    faces.push(...boxFaces(0,-.91,.10,.92,.37,.95,'PAYLOAD','#7a70aa'));
    faces.push(...boxFaces(-.52,-.43,.90,.38,.42,.21,'ADCS','#5d8498'));
    faces.push(...boxFaces(.87,.64,.15,.20,.2,.24,'COMMS','#688fad'));
    faces.sort((a,b)=>{const depth=a=>a.verts.reduce((s,v)=>s+p(v).z,0)/4;return depth(a)-depth(b)});
    const hex=(str)=>{const x=parseInt(str.slice(1),16);return[(x>>16)&255,(x>>8)&255,x&255]};
    const fill=(str,shade)=>{const [r,gr,b]=hex(str);return`rgb(${Math.min(255,r*shade)|0},${Math.min(255,gr*shade)|0},${Math.min(255,b*shade)|0})`};
    for(const face of faces){const pts=face.verts.map(p);g.beginPath();pts.forEach((q,i)=>i?g.lineTo(q.x,q.y):g.moveTo(q.x,q.y));g.closePath();const bright=[.78,1.08,.75,.94,.86,.68][face.face];let c=face.finish;if(face.id===active)c=color[active]||c;g.fillStyle=fill(c,bright);g.fill();g.strokeStyle=face.id===active?'#bafde4':'#26455c';g.lineWidth=face.id===active?1.6:.75;g.stroke()}
    // 3D antenna rods
    const line=(va,vb,col,width=2)=>{let a=p(va),b=p(vb);g.strokeStyle=col;g.lineWidth=width;g.beginPath();g.moveTo(a.x,a.y);g.lineTo(b.x,b.y);g.stroke()};
    line([.92,.75,.12],[1.65,1.22,.14],active==='COMMS'?'#bbffff':'#7eaccd',3);
    line([1.65,1.22,.14],[1.85,1.36,.10],active==='COMMS'?'#bbffff':'#7eaccd',2);
    // pseudo-axis attitude marker
    const axis=p([-.50,-.4,1.01]);g.strokeStyle='#9ab9ce';g.lineWidth=1.5;g.beginPath();g.arc(axis.x,axis.y,10,0,Math.PI*2);g.stroke();g.beginPath();g.moveTo(axis.x-14,axis.y);g.lineTo(axis.x+14,axis.y);g.stroke();
    // Ground-terminal fallback: pedestal, elevation yoke, concave reflector, feed tripod.
    // More detailed than a generic ellipse, but not a physical ground-station CAD model.
    let gx=w*.88,gy=h*.72;g.save();g.translate(gx,gy);g.scale(.78,.78);
    g.fillStyle='#172b3e';g.strokeStyle='#507184';g.lineWidth=1.3;
    g.fillRect(-58,29,120,9);g.strokeRect(-58,29,120,9);
    g.fillStyle='#597a90';g.fillRect(-11,-4,22,33);g.strokeRect(-11,-4,22,33);
    g.fillStyle='#314d61';g.fillRect(-22,-11,44,12);g.strokeRect(-22,-11,44,12);
    g.strokeStyle='#9ec1d0';g.lineWidth=5;g.beginPath();g.moveTo(-21,-24);g.lineTo(-11,-68);g.moveTo(21,-24);g.lineTo(11,-68);g.stroke();
    g.fillStyle='#95afbd';g.beginPath();g.ellipse(0,-77,47,24,-.15,0,Math.PI*2);g.fill();
    let disk=g.createLinearGradient(-46,-86,42,-58);disk.addColorStop(0,'#25465e');disk.addColorStop(.5,'#7497ab');disk.addColorStop(1,'#c1d4da');
    g.fillStyle=disk;g.strokeStyle='#d5e9ef';g.lineWidth=2;g.beginPath();g.ellipse(0,-77,45,21,-.15,0,Math.PI*2);g.fill();g.stroke();
    g.strokeStyle='#47647b';g.lineWidth=1;
    for(let j=0;j<8;j++){const ang=j*Math.PI/4;g.beginPath();g.moveTo(0,-77);g.lineTo(44*Math.cos(ang),-77+20*Math.sin(ang));g.stroke();}
    g.strokeStyle='#d4e3eb';g.lineWidth=1.6;
    for(const x of [-28,0,28]){g.beginPath();g.moveTo(x,-76);g.lineTo(20,-110);g.stroke();}
    g.fillStyle='#a0b9c7';g.fillRect(13,-118,17,13);g.strokeStyle='#3a5e75';g.strokeRect(13,-118,17,13);
    g.restore();
    // COMMS link is a visualized test condition, not a sampled RF waveform
    const antenna=p([1.80,1.38,.12]);if(active==='COMMS'){
      g.save();g.setLineDash([9,7]);g.lineDashOffset=this.motion?-(this.frame*16):0;g.strokeStyle=this.record?.status==='FAIL'?'#fd8c81':'#75dcf7';g.lineWidth=2.4;g.beginPath();g.moveTo(antenna.x,antenna.y);g.quadraticCurveTo(w*.73,h*.13,gx-18,gy-65);g.stroke();g.restore();
    }else{g.setLineDash([4,8]);g.strokeStyle='#386d83';g.lineWidth=1;g.beginPath();g.moveTo(antenna.x,antenna.y);g.lineTo(gx-18,gy-65);g.stroke();g.setLineDash([])}
    // Labeled subsystem markers and test status (controller only)
    const status=this.record?.status,labels=['EPS','THERMAL','OBC','ADCS','PAYLOAD','COMMS'];
    const labelMode=document.getElementById('missionLabelMode')?.value||'focus';
    labels.forEach((id,i)=>{const anchor=p(this.anchors[id]),x=anchor.x,y=anchor.y;const selected=active===id;const failure=selected&&status==='FAIL';if(selected){g.save();g.strokeStyle=failure?'#ff7e86':'#75e6bc';g.lineWidth=2.5;g.shadowBlur=22;g.shadowColor=g.strokeStyle;g.beginPath();g.arc(x,y,21+(this.motion?2*Math.sin(this.frame*3):0),0,7);g.stroke();g.restore()}
      if(labelMode==='none'||(labelMode==='focus'&&!selected))return;
      const dx=(id==='COMMS'?27:id==='OBC'?-30:id==='PAYLOAD'?28:(i%2?-36:-45)),dy=id==='ADCS'?34:id==='PAYLOAD'?31:-22;
      g.font='bold 9px system-ui';g.textAlign='left';const lx=x+dx,ly=y+dy,tw=g.measureText(id).width+10;g.fillStyle=selected?'#16483d':'#0a2134';g.strokeStyle=selected?'#69e2be':'#3b6278';g.lineWidth=1;g.beginPath();g.roundRect(lx-4,ly-12,tw,16,4);g.fill();g.stroke();g.fillStyle=selected?'#c8ffed':'#b5d5e8';g.fillText(id,lx+3,ly);});
    // Suspicion is NOT a physical fault localization: top known hypothesis gets amber ring.
    let top=Object.entries(this.prior||{}).filter(([k])=>k!=='healthy').sort((a,b)=>b[1]-a[1])[0];if(top&&this.record&&top[1]>=.25){const sys=HYP_TO_SYS[top[0]];if(sys){const t=p(this.anchors[sys]);g.strokeStyle='#ffc47b';g.setLineDash([4,5]);g.beginPath();g.arc(t.x,t.y,28,0,7);g.stroke();g.setLineDash([])}}
    // Fault truth is completely invisible until explicit post-run reveal.
    if(this.showTruth){const curTime=this.record?.end_s||0;this.truth.filter(f=>f.onset_s<=curTime&&curTime<f.end_s).forEach(f=>{const sys=HYP_TO_SYS[f.mechanism];if(!sys)return;const t=p(this.anchors[sys]);g.strokeStyle='#ff92cb';g.lineWidth=2.6;g.beginPath();g.arc(t.x,t.y,34,0,Math.PI*2);g.stroke();g.fillStyle='#ffb5dd';g.font='bold 10px system-ui';g.fillText('INJECTED',t.x+24,t.y+18)})}
    // When a requirement fails, magnify the region checked by that test. This is
    // evidence localization, not validated physical root-cause localization.
    if(active&&this.record?.status==='FAIL'&&w>680){
      const a=p(this.anchors[active]);const sw=110,sh=90,destW=194,destH=148;
      const source=document.createElement('canvas');source.width=sw;source.height=sh;
      const x0=Math.max(0,Math.min(w-sw,a.x-sw/2)),y0=Math.max(0,Math.min(h-sh,a.y-sh/2));
      source.getContext('2d').drawImage(canvas,x0*(canvas.width/w),y0*(canvas.height/h),sw*(canvas.width/w),sh*(canvas.height/h),0,0,sw,sh);
      const rx=w-destW-17,ry=42;g.fillStyle='#0b2032';g.fillRect(rx-5,ry-20,destW+10,destH+32);
      g.strokeStyle='#ff848e';g.lineWidth=1.5;g.strokeRect(rx-5,ry-20,destW+10,destH+32);
      g.drawImage(source,rx,ry,destW,destH);g.font='bold 11px system-ui';g.fillStyle='#ffc2c6';g.textAlign='left';
      g.fillText('FAILED CHECK REGION · '+active,rx,ry-6);
      g.fillStyle='#9bbbd0';g.font='10px system-ui';g.fillText('Cause not established',rx+5,ry+destH+12);
    }
    g.fillStyle='#a5c2d5';g.font='10px system-ui';g.textAlign='center';g.fillText('SIMULATED SPACECRAFT',w*.36,h-18);g.fillText('GROUND STATION',gx,h-18);
    g.textAlign='left';g.fillStyle='#83a5bd';g.font='10px system-ui';g.fillText('Drag to rotate · scroll to zoom',15,22);
  }
 }
 window.SATVV_MissionView=MissionView;
})();
