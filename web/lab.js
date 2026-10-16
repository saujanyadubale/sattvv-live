'use strict';
const $=id=>document.getElementById(id);
const labels={
healthy:['Healthy spacecraft','No fault injected'],resistance_ramp:['Gradual battery degradation','Battery resistance develops over time'],intermittent_resistance:['Intermittent electrical fault','Electrical fault appears and recovers'],sensor_drift:['Temperature sensor drift','One sensor diverges from true temperature'],heater_fault:['Abnormal heater operation','Temperature rises more rapidly than expected'],radio_burst:['Communications packet-loss burst','Temporary bursts of lost radio packets'],normal_load_cycle:['Healthy load variation','Normal changes in electrical demand'],adcs_wheel_weak:['Reaction-wheel weakness','Reduced actuator effectiveness'],adcs_gyro_bias:['Gyroscope bias','Rotation measurement deviates'],adcs_star_dropout:['Star-tracker dropout','Intermittent loss of attitude reference'],healthy_eclipse_and_load:['Healthy eclipse and load variation','Healthy complex operating conditions'],dual_resistance_sensor:['Battery degradation + sensor drift','Simultaneous electrical and sensor faults'],heater_plus_radio:['Heater + communications fault','Compound thermal and radio fault'],wheel_plus_battery:['Reaction-wheel + battery fault','Coupled electrical and ADCS faults'],slow_resistance_unseen:['Unfamiliar battery degradation','Unseen gradual-resistance pattern'],radio_plus_gyro_bias:['Communications + gyro faults','Compound radio and ADCS fault'],healthy_eclipse:['Healthy eclipse','Healthy power-system eclipse case']};
const policies={fixed:['Fixed-order testing','Follow a predefined test list'],temporal_adaptive:['Temporal adaptive','Prioritize stale requirement checks and telemetry warnings'],information_gain:['Bayesian information gain','Choose informative tests to distinguish fault hypotheses'],learned_risk:['ML-ranked testing','Offline-trained Random Forest ranks tests by estimated failure risk'],predictive_active:['Risk-aware predictive planner','Short-budget greedy fallback, otherwise three-test lookahead using observable risk and coverage']};
const stress=['healthy_eclipse_and_load','dual_resistance_sensor','heater_plus_radio','wheel_plus_battery','slow_resistance_unseen','radio_plus_gyro_bias','healthy_eclipse'];
let current=null;let requestVersion=0;let compareVersion=0;
function name(v){return labels[v]?.[0]||v?.replaceAll('_',' ')||'Not estimated'}
function setup(){for(const [key,value]of Object.entries(labels))$('scenario').add(new Option(value[0],key));$('scenario').value='resistance_ramp';for(const [key,value]of Object.entries(policies)){$('policy').add(new Option(value[0],key))}$('policy').value='predictive_active';for(const id of ['scenario','policy','budget','severity','soc','onset','seed','eclipse','horizon','detector'])$(id).addEventListener('input',()=>{refresh();invalidateResults()});document.querySelectorAll('.tabs button').forEach(btn=>btn.onclick=()=>{for(const b of document.querySelectorAll('.tabs button'))b.classList.toggle('active',b===btn);for(const section of document.querySelectorAll('.workspace'))section.hidden=section.id!==btn.dataset.tab});for(const key of ['fixed','temporal_adaptive','information_gain','learned_risk','predictive_active']){const el=document.createElement('label');const chk=document.createElement('input');chk.type='checkbox';chk.value=key;chk.checked=key==='fixed'||key==='information_gain';el.append(chk,' '+policies[key][0]);$('compareChecks').append(el);chk.addEventListener('change',()=>{compareVersion++;$('compareRows').replaceChildren();$('compareContext').textContent='Strategy selection changed. Run the comparison again.'})}$('run').onclick=runExperiment;$('runCompare').onclick=runCompare;$('export').onclick=exportResult;refresh(); const page=location.hash.slice(1); if(['compare','research','experiment'].includes(page))document.querySelector(`.tabs button[data-tab="${page}"]`)?.click();fetch('/api/catalog').then(r=>r.json()).then(x=>{for(const t of x.procedures){const tr=document.createElement('tr');for(const v of [t.id,t.name,t.subsystem,t.cost_min+' min',t.requirements.join(', ')]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('catalog').append(tr)}}).catch(()=>{})}
function invalidateResults(){requestVersion++;compareVersion++;current=null;$('results').hidden=true;$('empty').hidden=false;$('empty').textContent='Settings changed. Run the experiment to update these results.';$('compareRows').replaceChildren();$('compareContext').textContent='Settings changed. Re-run the comparison.';}
function refresh(){let s=$('scenario').value,lock=stress.includes(s);$('scenarioDesc').textContent=labels[s]?.[1]||'';$('policyDesc').textContent=policies[$('policy').value]?.[1]||'';$('budgetVal').textContent=$('budget').value+' min';$('severityVal').textContent=Number($('severity').value).toFixed(1)+'×';$('socVal').textContent=$('soc').value+'%';for(const id of ['severity','soc','eclipse'])$(id).disabled=lock;$('controlHint').textContent=lock?'Stress cases intentionally choose their own fault severity, eclipse and initial charge from the random seed. Those controls are disabled here, not silently ignored.':'Fault severity, eclipse and battery charge are passed to the integrated simulator. Forecast controls take effect in v0.9.3.'}
function settings(){return{scenario:$('scenario').value,policy:$('policy').value,budget_min:Number($('budget').value),onset_s:Number($('onset').value)*60,seed:Number($('seed').value),severity:Number($('severity').value),initial_soc:Number($('soc').value)/100,eclipse:$('eclipse').checked,horizon_s:Number($('horizon').value),detector:$('detector').value}}
function requestPayload(s){return{experiment:stress.includes(s.scenario)?'stress':'integrated',scenario:s.scenario,policy:s.policy,budget_min:s.budget_min,onset_s:s.onset_s,seed:s.seed,...(!stress.includes(s.scenario)?{severity:s.severity,initial_soc:s.initial_soc,eclipse:s.eclipse}:{})}}
async function post(url,payload){const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw Error(data.error||JSON.stringify(data));return data}
async function execute(s){return post('/api/lab-run',s)}
const minutes=s=>s==null?'—':(s/60).toFixed(s%60===0?0:1)+' min';
async function runExperiment(){
const btn=$('run'),s=settings(),req=++requestVersion;
btn.disabled=true;btn.textContent='Running simulation…';$('mainCompute').hidden=false;$('error').textContent='';
try{const data=await execute(s);
if(req!==requestVersion)return;
if(data.meta?.policy!==s.policy||data.display_policy!==s.policy||
(data.evidence||[]).some(r=>r.decision?.selected_policy!==s.policy))
throw Error('Policy mismatch in returned evidence. Please export the result and report this bug.');
render(data);
}catch(e){if(req===requestVersion)$('error').textContent=e.message}
finally{$('mainCompute').hidden=true;btn.disabled=false;btn.textContent='▶ Run spacecraft experiment'}
}
function render(data){current=data;$('runContext').textContent='Executed strategy: '+(policies[data.meta.policy]?.[0]||data.meta.policy)+' · Scenario: '+name(data.meta.scenario)+' · Seed: '+data.meta.seed+' · Budget: '+data.meta.budget_min+' min';$('empty').hidden=true;$('results').hidden=false;$('resultStatus').textContent=data.detected?'Failed requirement found':'No failure verified';$('cause').textContent=name(data.estimated_cause);$('confidence').textContent=data.cause_confidence==null?'No probabilistic estimate':'Hypothesis weight '+(100*data.cause_confidence).toFixed(1)+'% (uncalibrated)';$('spent').textContent=minutes(data.spent_s);$('count').textContent=data.tests_run??data.evidence?.length??0;$('plainSummary').textContent=data.detected?'A completed verification check failed a requirement. This does not establish the exact root cause.':'No executed test failed during this budget. This does not prove that all requirements or all fault mechanisms are healthy.';
const evidence=data.evidence||[];const last=evidence.at(-1),stages=data.stages;
$('decisionSummary').textContent=stages?.verification?.summary||`The ${policies[data.meta.policy]?.[0]||'selected'} scheduler chose the procedures below. Each outcome is based on executed checks, not the hidden injected fault label.`;
const elements=[...$('stages').children];if(stages){for(const [i,k]of ['detection','forecasting','diagnosis','verification','audit'].entries())elements[i].querySelector('p').textContent=stages[k]?.summary||'No result';const v=stages.forecasting?.latest?.bus_voltage_v;const t=stages.forecasting?.latest?.temperature_c;const h=data.meta.horizon_s/60;
$('stageNote').textContent=(v&&t)?`From the last decision: ${h}-minute voltage forecast ${v.ml_estimate.toFixed(2)} V (synthetic uncertainty band ${v.lower.toFixed(2)}–${v.upper.toFixed(2)} V), temperature forecast ${t.ml_estimate.toFixed(1)} °C. Warnings and forecasts do not count as FAIL.`:'Integrated results use only measurements available before each test decision.'}else{$('stageNote').textContent='Only the new integrated endpoint provides a shared five-stage loop.';for(const e of elements)e.querySelector('p').textContent='Separate research component'}
const body=$('trace');body.replaceChildren();for(const r of evidence){const tr=document.createElement('tr');tr.dataset.row='1';for(const v of [minutes(r.end_s),(r.test_id||'Observe')+' · '+(r.test_name||''),r.status||'—',r.decision?.reason|| (r.decision?.expected_information_bits==null?'—':Number(r.decision.expected_information_bits).toFixed(3)+' bits')]){const td=document.createElement('td');td.textContent=String(v);tr.append(td)}tr.onclick=()=>renderEvidence(r,data);body.append(tr)}
$('evidence').textContent='Select a test to inspect requirement outcomes, measured limits and decision provenance.';$('evidenceRaw').textContent='Select a verification step.';if(evidence.some(r=>r.status==='FAIL'))renderEvidence(evidence.find(r=>r.status==='FAIL'),data);
const observations=data.observations||evidence.map(r=>r.telemetry_end).filter(Boolean);draw('voltageChart',observations.map(p=>({x:p.time_s/60,y:p.bus_voltage_v})).filter(p=>Number.isFinite(p.y)),'#72e0bf');draw('beliefChart',evidence.filter(r=>r.posterior).map(r=>({x:r.end_s/60,y:Math.max(...Object.values(r.posterior))})),'#e4be84');}
function renderEvidence(rec,result){
 const root=$('evidence');root.replaceChildren();$('evidenceRaw').textContent=JSON.stringify(rec,null,2);
 const make=(tag,txt,cls)=>{let e=document.createElement(tag);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e};
 root.append(make('div',`${rec.test_id} · ${rec.test_name} — ${rec.status}`,'evidence-head'));
 root.append(make('p',`Selected by ${policies[rec.decision?.selected_policy]?.[0]||'unknown'} at ${minutes(rec.decision?.observation_time_s)}. ${({repeat_streak_limit:'Coverage safeguard forced a previously untested procedure after multiple repeats',coverage_budget_reserve:'Coverage safeguard reserved time for untested safe procedures'})[rec.decision?.coverage_guard]||rec.decision?.reason||'Selection reason unavailable'}.`,'evidence-sub'));
 const grid=make('div',null,'evidence-grid');
 for(const [req,passed] of Object.entries(rec.checks||{})){
    const box=make('div',null,'evidence-metric'),data=rec.check_details?.[req];
    box.append(make('b',`${req}: ${passed===true?'PASS':passed===false?'FAIL':'INCONCLUSIVE'}`));
    if(data){
      box.append(make('span',data.metric));
      box.append(make('span',data.measured==null?'Measurement unavailable':`Measured: ${Number(data.measured).toFixed(4)} ${data.unit||''}`));
      box.append(make('span',`Requirement: ${data.operator} ${data.threshold} ${data.unit||''}`));
      const gap=data.measured==null?null:(data.operator==='<='||data.operator==='<')?Number(data.threshold)-Number(data.measured):Number(data.measured)-Number(data.threshold);
      if(gap!=null)box.append(make('span',`Margin: ${gap.toFixed(4)} ${data.unit||''} (${gap>=0?'within limit':'outside limit'})`));
      if(data.context)box.append(make('span',data.context));
    }else{
      box.append(make('span','Boolean verification result. A numerical threshold/measurement pair was not recorded for this requirement in this procedure.'));
    }
    grid.append(box);
 }
 root.append(grid);
 const tm=rec.telemetry_end||{};
 root.append(make('p',`End-of-test telemetry: bus voltage ${typeof tm.bus_voltage_v==='number'?tm.bus_voltage_v.toFixed(3)+' V':'—'} · current ${typeof tm.bus_current_a==='number'?tm.bus_current_a.toFixed(3)+' A':'—'} · temperature ${typeof tm.temperature_c==='number'?tm.temperature_c.toFixed(2)+' °C':'—'}. These final samples may differ from the worst values measured during a test.`,'evidence-sub'));
 if(!result.audit?.passed)root.append(make('p','Evidence audit flagged inconsistencies: '+(result.audit?.problems||[]).join('; '),'mismatch'));
}
function draw(id,points,color){const c=$(id),w=c.clientWidth||400,h=c.clientHeight||215,dpr=window.devicePixelRatio||1;c.width=w*dpr;c.height=h*dpr;const ctx=c.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);ctx.font='11px sans-serif';ctx.fillStyle='#a8bdd4';if(!points.length){ctx.fillText('No recorded samples',22,h/2);return}let xs=points.map(p=>p.x),ys=points.map(p=>p.y),x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);if(x0===x1)x1++;if(y0===y1){y0-=.1;y1+=.1}const xx=x=>38+(x-x0)/(x1-x0)*(w-53),yy=y=>h-27-(y-y0)/(y1-y0)*(h-49);for(let i=0;i<4;i++){let y=23+i*(h-50)/3;ctx.strokeStyle='#294056';ctx.beginPath();ctx.moveTo(38,y);ctx.lineTo(w-15,y);ctx.stroke();ctx.fillText((y1-i*(y1-y0)/3).toFixed(2),2,y+4)}ctx.fillText(x0.toFixed(0)+'m',38,h-5);ctx.fillText(x1.toFixed(0)+'m',w-42,h-5);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(xx(p.x),yy(p.y)):ctx.moveTo(xx(p.x),yy(p.y)));ctx.stroke();}
async function runCompare(){
 const btn=$('runCompare'),s=settings(),ticket=++compareVersion;
 btn.disabled=true;$('compareCompute').hidden=false;$('compareError').textContent='';$('compareRows').replaceChildren();
 $('compareContext').textContent=`Scenario: ${name(s.scenario)} · Seed ${s.seed} · Budget ${s.budget_min} min · Fault onset ${s.onset_s/60} min`;
 try{
 const chosen=[...document.querySelectorAll('#compareChecks input:checked')].map(x=>x.value);
 if(!chosen.length)throw Error('Select at least one strategy');
 for(const policy of chosen){
   if(ticket!==compareVersion)return;
   btn.textContent='Running '+policies[policy][0]+'…';
   const result=await execute({...s,policy});
   if(ticket!==compareVersion)return;
   if(result.meta?.policy!==policy||result.display_policy!==policy||
      (result.evidence||[]).some(rec=>rec.decision?.selected_policy!==policy))
      throw Error('Mismatch between requested and executed test policy: '+policy);
   const tr=document.createElement('tr');
   for(const v of [policies[policy][0],result.detected?'Yes':'No',minutes(result.spent_s),result.tests_run,name(result.estimated_cause)]){
     const td=document.createElement('td');td.textContent=v;tr.append(td);
   }
   $('compareRows').append(tr);
 }
 }catch(e){if(ticket===compareVersion)$('compareError').textContent=e.message}
 finally{$('compareCompute').hidden=true;btn.disabled=false;btn.textContent='▶ Compare selected strategies'}
}
function exportResult(){if(!current)return;const blob=new Blob([JSON.stringify(current,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='satvv-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
setup();

window.addEventListener("hashchange",()=>{const page=location.hash.slice(1);const b=document.querySelector(`.tabs button[data-tab="${page}"]`);if(b)b.click()});
