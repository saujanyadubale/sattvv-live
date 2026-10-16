'use strict';
/* Data explanation is a read-only presentation layer. Hidden injected fault
   labels are deliberately never consulted for warnings or advisories. */
(function(){
let result=null, cursor=null;
const DOM=id=>document.getElementById(id);
const normalV=(soc,load)=>{const voc=7.25+.6*Math.max(0,Math.min(1,(soc||0)/100));const disc=voc*voc-4*.12*Math.max(0,load||0);return disc>=0?(voc+Math.sqrt(disc))/2:voc*.5};
const notes={
 bus_voltage_v:'Bus voltage powers onboard electronics. Compare its value against battery charge, operating mode and electrical load; a decline alone is not proof of degradation.',
 bus_current_a:'Bus current changes when loads and operating modes change. A sudden current change can be expected during a verification procedure.',
 battery_soc_pct:'Battery charge estimates stored energy. Eclipse and payload loads can decrease it without implying a battery fault.',
 temperature_c:'Equipment temperature responds to power consumption and the thermal environment. Compare the redundant sensor before inferring a physical heater problem.',
 redundant_temperature_c:'The independent temperature channel helps check whether a thermal change is genuine or one sensor is drifting.',
 sensor_delta:'Persistent disagreement between temperature channels may provide an early warning, even when their formal 3 °C agreement check still passes.',
 packet_loss_fraction:'Packet-loss fraction measures lost communications during downlink activity. Interpret it with communication mode and test-window measurements.',
 load_w:'Power demand helps explain changes in current, heating and voltage; a higher load can cause a normal voltage sag.',
 solar_w:'Available solar power depends on the illumination state. Solar reduction during eclipse is expected.',
 latency_ms:'Packet latency may change with retries and the communication environment. Compare with test-specific requirements.'};
const units={bus_voltage_v:'V',bus_current_a:'A',battery_soc_pct:'%',temperature_c:'°C',redundant_temperature_c:'°C',sensor_delta:'°C',packet_loss_fraction:'fraction',load_w:'W',solar_w:'W',latency_ms:'ms'};
function sampleValue(r,key){if(key==='sensor_delta')return Math.abs((r.temperature_c||0)-(r.redundant_temperature_c||0));return Number(r[key])}
function expected(r,key){if(key==='bus_voltage_v')return normalV(r.battery_soc_pct,r.load_w);if(key==='temperature_c')return r.redundant_temperature_c;if(key==='redundant_temperature_c')return r.temperature_c;if(key==='sensor_delta')return 0;return null}
const limits={bus_voltage_v:{v:6.7,dir:'min',label:'Project forecast limit'},temperature_c:{v:70,dir:'max',label:'T06/T15 thermal requirement'},sensor_delta:{v:3,dir:'max',label:'T11 sensor agreement'}};
const keyForCanvas=id=>id==='chVoltage'?DOM('leftSignal').value:DOM('rightSignal').value;
const redraw=()=>{if(!result)return;updateCharts(result.evidence?.[stepIndex]?.end_s||0)};
function renderChart(id,items,key,color,seconds){
 const can=DOM(id),w=Math.max(260,can.clientWidth||390),h=230,dpr=window.devicePixelRatio||1;
 can.width=Math.round(w*dpr);can.height=Math.round(h*dpr);let ctx=can.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
 const mode=DOM('chartMode').value;
 const rows=(items||[]).filter(r=>Number.isFinite(sampleValue(r,key))&&r.time_s<=seconds);
 if(!rows.length){ctx.fillStyle='#9cb4c9';ctx.fillText('Replay to display measurements',16,35);return}
 let values=rows.map((r,i)=>{
  const v=sampleValue(r,key),e=expected(r,key);
  if(mode==='residual')return e!=null?v-e:i? v-sampleValue(rows[i-1],key):0;
  if(mode==='change')return i? v-sampleValue(rows[i-1],key):0;
  return v;
 });
 const expectedValues=mode==='expected'?rows.map(r=>expected(r,key)):[];
 const special=limits[key],plotLimit=mode==='raw'&&special?special.v:null;
 const full=values.concat(expectedValues.filter(Number.isFinite));if(plotLimit!==null)full.push(plotLimit);
 let lo=Math.min(...full),hi=Math.max(...full);let pad=(hi-lo||.5)*.16;lo-=pad;hi+=pad;
 const left=49,right=w-17,top=26,bottom=h-30;
 const xx=t=>left+Math.max(0,t)/Math.max(60,seconds)*(right-left), yy=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
 ctx.font='11px system-ui';ctx.lineWidth=1;
 for(let i=0;i<4;i++){let y=top+(bottom-top)*i/3;ctx.strokeStyle='#24465c';ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle='#a5c3d3';ctx.fillText((hi-(hi-lo)*i/3).toFixed(2),3,y+3)}
 ctx.fillStyle='#aac8d9';ctx.fillText('0 min',left,bottom+19);ctx.fillText(Math.round(seconds/60)+' min',right-34,bottom+19);
 const line=(series,stroke,dashed=false)=>{ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.setLineDash(dashed?[5,5]:[]);ctx.beginPath();series.forEach((v,i)=>{if(!Number.isFinite(v))return;i?ctx.lineTo(xx(rows[i].time_s),yy(v)):ctx.moveTo(xx(rows[i].time_s),yy(v))});ctx.stroke();ctx.setLineDash([])};
 if(plotLimit!==null){ctx.strokeStyle='#f3a2a1';ctx.setLineDash([7,6]);ctx.beginPath();ctx.moveTo(left,yy(plotLimit));ctx.lineTo(right,yy(plotLimit));ctx.stroke();ctx.setLineDash([])}
 if(mode==='expected'&&expectedValues.some(Number.isFinite))line(expectedValues,'#e2bb7c',true);
 line(values,color);
 for(const e of (result.insights_v11?.warning_events||[]).filter(x=>x.time_s<=seconds)){
   if(e.time_s<0)continue;ctx.strokeStyle='#e6b76e';ctx.lineWidth=.8;ctx.setLineDash([2,6]);ctx.beginPath();ctx.moveTo(xx(e.time_s),top);ctx.lineTo(xx(e.time_s),bottom);ctx.stroke();ctx.setLineDash([]);
 }
 if(cursor!==null&&cursor<=seconds){ctx.strokeStyle='#b5b6ff';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(xx(cursor),top);ctx.lineTo(xx(cursor),bottom);ctx.stroke()}
 ctx.fillStyle='#a7c4d5';ctx.font='10px system-ui';ctx.fillText(mode==='raw'&&plotLimit!==null?'red dashed: project requirement / reference':mode==='expected'?'cyan/orange: observed vs expected or sensor reference':mode==='residual'?'Measured minus expected (or successive change if no model)':'Telemetry · replay synchronized',left,13);
}
const orig=window.tinyCanvas || tinyCanvas;
window.tinyCanvas=tinyCanvas=function(id,items,key,color,seconds){renderChart(id,items,key,color,seconds)};
function interpretAt(t){
 if(!result)return;const samples=(result.observations||[]).filter(x=>x.time_s<=t);
 const last=samples.at(-1);if(!last)return;
 const lv=DOM('leftSignal').value,rv=DOM('rightSignal').value;
 const present=[lv,rv].map(k=>{let val=sampleValue(last,k);const exp=expected(last,k);return `<b>${(SIGNALS[k]||[k])[0]}:</b> ${Number.isFinite(val)?val.toFixed(3):'—'} ${units[k]||''}${exp!=null?` · expected/reference ${exp.toFixed(3)}`:''}`}).join(' &nbsp; · &nbsp; ');
 const limitsText=[lv,rv].filter(k=>limits[k]).map(k=>`${(SIGNALS[k]||[k])[0]}: ${limits[k].dir==='min'?'≥':'≤'} ${limits[k].v} ${units[k]}`).join('; ');
 DOM('interpretPanel').innerHTML=`<h3>What do these signals tell us at ${Math.round(last.time_s/60)} min?</h3><p>${notes[lv]} ${lv!==rv?notes[rv]:''}</p><p>${present}</p><p class="help">${limitsText||'No single global pass/fail threshold is defined for this selected quantity.'} · Only the executed test's own requirements establish PASS/FAIL.</p>`;
}
function safeText(elm,txt){elm.textContent=txt}
function updateStep(r,cutoff,rec){if(!result)return;
 const el=DOM('healthStatus'),all=r.insights_v11||{},alerts=(all.warning_events||[]).filter(a=>a.time_s<=cutoff),failed=(r.evidence||[]).filter(e=>e.end_s<=cutoff&&e.status==='FAIL');
 const label=failed.length?'Verified requirement failure':alerts.length?'Early deviation warning':'No detected warning in observed samples';
 if(!failed.length&&alerts.length)DOM('chInterpret').textContent=`Early warning at ${(alerts[0].time_s/60).toFixed(1)} min: suspicious ${alerts[0].subsystem} telemetry. No executed requirement has failed. This is not a confirmed root cause.`;
 safeText(el,label+` · ${alerts.length} warning event(s) by this replay time. Warning ≠ verification FAIL.`);
 const root=DOM('insightEvents');root.replaceChildren();for(const warn of alerts.slice(-4)){
  let d=document.createElement('div');d.className='insight-event';d.textContent=`${(warn.time_s/60).toFixed(1)} min · ${warn.subsystem} · ${warn.metric}${warn.measured!=null?' ('+warn.measured+')':''}`;root.append(d)}
 const advice=DOM('actionAdvice');advice.replaceChildren();const focus=failed.at(-1)?.subsystem||alerts.at(-1)?.subsystem;
 const playbook={EPS:['Check voltage behavior under measured load and charge conditions (T03/T14).','Review load-shedding options only with approved spacecraft constraints.'],THERMAL:['Compare both thermal sensors and trends under stable operating conditions (T11/T16).','Review sensor calibration/redundancy, subject to mission operations approval.'],COMMS:['Review downlink packet loss, retries, and pointing state (T05/T08).','Review ground link budget, coding, and authorized retry parameters.'],ADCS:['Compare gyro/star-tracker measurements and wheel response (T17–T20).','Review approved attitude-control recovery procedures.'],OBC:['Review watchdog events and mode transitions (T01/T10/T12).','Review controlled recovery playbooks before considering a reset.'],PAYLOAD:['Check payload load, duty cycle and thermal recovery (T04/T09/T15).','Review approved workload reduction only after validating margins.']}[focus];
 for(const text of playbook||['No particular subsystem is implicated by the observed evidence.','Continue normal verification or select a relevant cross-check.']){
  let p=document.createElement('p');p.textContent=text;advice.append(p)}
 if(!failed.length&&alerts.length===0)DOM('actionPanel').dataset.status='neutral';else DOM('actionPanel').dataset.status=failed.length?'fail':'warning';
 interpretAt(cursor===null?cutoff:Math.min(cursor,cutoff));
}
function attachCursor(){for(const id of ['chVoltage','chTemp'])DOM(id).addEventListener('mousemove',e=>{
 if(!result)return;const c=DOM(id),rect=c.getBoundingClientRect(),frac=Math.max(0,Math.min(1,(e.clientX-rect.left-49)/Math.max(1,rect.width-66))),end=result.evidence?.[stepIndex]?.end_s||0;
 cursor=frac*end;const nearest=(result.observations||[]).filter(x=>x.time_s<=end).reduce((a,b)=>!a||Math.abs(b.time_s-cursor)<Math.abs(a.time_s-cursor)?b:a,null);
 if(nearest){cursor=nearest.time_s;safeText(DOM('cursorReadout'),`Linked cursor at ${Math.round(cursor/60)} min · Mode: ${nearest.mode||'—'} · Measured bus voltage ${Number(nearest.bus_voltage_v||0).toFixed(3)} V · Primary/secondary temperature ${Number(nearest.temperature_c||0).toFixed(2)} / ${Number(nearest.redundant_temperature_c||0).toFixed(2)} °C`);interpretAt(cursor)}redraw();
 });}
const api={result(r){result=r;cursor=null;DOM('cursorReadout').textContent='Move over either graph for a synchronized view of both measurements.'},step:updateStep};
window.SATVV_INTERPRET=api;
DOM('chartMode').addEventListener('change',()=>{redraw();if(result)updateStep(result,result.evidence?.[stepIndex]?.end_s||0,result.evidence?.[stepIndex]);});
attachCursor();
})();
