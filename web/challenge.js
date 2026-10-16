'use strict';
const $=id=>document.getElementById(id);
const POLICY={fixed:'Fixed-order',temporal_adaptive:'Temporal adaptive',information_gain:'Information gain',learned_risk:'ML-ranked',predictive_active:'Predictive planner (v1.0.3)'};
const HYP={healthy:'Healthy / no known fault',resistance_ramp:'Battery degradation',intermittent_resistance:'Intermittent battery',sensor_drift:'Thermal sensor drift',heater_fault:'Heater fault',radio_burst:'Radio packet loss',adcs_gyro_bias:'Gyro bias',adcs_wheel_weak:'Wheel weakness',adcs_star_dropout:'Star-tracker dropout'};
const SUBSYSTEM=['EPS','THERMAL','OBC','COMMS','PAYLOAD','ADCS'];
const COVERAGE_EXPLANATION={repeat_streak_limit:'Coverage safeguard: prioritized an untested procedure after repeated checks',coverage_budget_reserve:'Coverage safeguard: reserved time for untested safe procedures',bounded_sequence_lookahead:'Risk-aware three-test lookahead, replanned after each completed procedure'};
const SIGNALS={
 bus_voltage_v:['Bus voltage','V'],temperature_c:['Temperature','°C'],
 redundant_temperature_c:['Second temperature sensor','°C'],sensor_delta:['Sensor disagreement','°C'],
 bus_current_a:['Bus current','A'],battery_soc_pct:['Battery charge','%'],
 load_w:['Power load','W'],solar_w:['Solar input','W'],packet_loss_fraction:['Packet loss fraction','0–1'],
 latency_ms:['Packet latency','ms']
};
function samples(){return (current?.observations||[]).map(x=>({...x,sensor_delta:(Number(x.temperature_c)-Number(x.redundant_temperature_c))}));}
function updateCharts(cutoff){const data=samples();for(const [sel,canvas,title,color] of [['leftSignal','chVoltage','leftSignalTitle','#69e4c7'],['rightSignal','chTemp','rightSignalTitle','#fac18a']]){
 const key=$(sel).value;stext(title,SIGNALS[key][0].toUpperCase()+' ('+SIGNALS[key][1]+')');tinyCanvas(canvas,data,key,color,Math.max(cutoff,60));
}}
function startComputing(){document.body.classList.add('is-computing');$('mainCompute').hidden=false;$('startChallenge').setAttribute('aria-busy','true');if(computeTimer)clearInterval(computeTimer);$('computePanel').hidden=false;const m=['Running simulation and test procedures…','Recording measured evidence…','Preparing the replay and diagnostics…'];let n=0;stext('computeMessage',m[n]+' This animation is not a backend progress measurement.');computeTimer=setInterval(()=>{n=(n+1)%m.length;stext('computeMessage',m[n]+' This animation is not a backend progress measurement.')},1800)}
function stopComputing(){document.body.classList.remove('is-computing');$('mainCompute').hidden=true;$('startChallenge').removeAttribute('aria-busy');if(computeTimer)clearInterval(computeTimer);computeTimer=null;$('computePanel').hidden=true}
function exposureSummary(result){const root=$('faultExposure');root.hidden=true;root.replaceChildren();if(result.meta?.experiment_mode==='manual'){root.append(el('p','Manual scenario: you selected the fault type in advance. There is no hidden random oracle to reveal.','help'));return}if(result.oracle_after_run?.healthy){root.append(el('p','Healthy negative control: no faults were injected.','help'));return}
 root.append(el('p','If a fault was injected but not detected, review its duration and whether a relevant procedure was running. Overlap is not proof that the fault was strong enough to fail.','help'));
 for(const f of result.challenge_assessment?.fault_exposures||[]){const box=el('div',null,'exposure-card');box.append(el('strong',`${HYP[f.fault]||f.fault}: ${fmt(f.onset_s)}–${fmt(f.end_s)} (${fmt(f.duration_s)})`));box.append(el('p',`Severity ${f.severity} · Relevant procedures: ${f.relevant_tests.join(', ')}`));box.append(el('p',f.overlapping_checks.length?'Overlapping checks: '+f.overlapping_checks.map(x=>x.test_id+' '+x.result).join(', '):'No relevant check overlapped this episode.'));for(const hit of f.overlapping_checks){for(const d of Object.values(hit.check_details||{})){if(typeof d?.measured==='number'&&typeof d?.threshold==='number')box.append(el('p',`${hit.test_id}: ${d.metric||'Measured value'} ${d.measured.toFixed(3)} ${d.unit||''} · limit ${d.operator} ${d.threshold.toFixed(3)} ${d.unit||''}`));}}
box.append(el('p',f.explanation));root.append(box)}}

let current=null,stepIndex=-1,timer=null,requestSerial=0,truthShown=false,computeTimer=null;
const mission=new window.SATVV_MissionView($('missionCanvas'));
const stext=(id,value)=>$(id).textContent=String(value);
const fmt=t=>t==null?'—':(t/60).toFixed(t%60?1:0)+' min';
function settings(){const base={mode:$('experimentMode').value,policy:$('chPolicy').value,seed:Number($('chSeed').value),budget_min:Number($('chBudget').value)};
 if(base.mode==='random')return {...base,difficulty:$('difficulty').value,intensity:$('intensity').value};
 const onset=Math.max(0,Number($('manualOnset').value));return {...base,scenario:$('manualScenario').value,onset_s:Math.round(onset*6)*10,
 severity:Number($('manualSeverity').value),initial_soc:Number($('manualSoc').value)/100,
 eclipse:$('manualEclipse').checked,horizon_s:Number($('manualHorizon').value),detector:$('manualDetector').value};}
function stop(){if(timer){clearInterval(timer);timer=null}stext('playPause','▶ Play')}
async function post(payload){const reply=await fetch('/api/unified',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});let data=await reply.json();if(!reply.ok)throw Error(data.error||'Challenge request failed');return data}
function stage(which){document.querySelectorAll('#stageRail>div').forEach((el,i)=>{el.classList.toggle('stage-now',i===which);el.classList.toggle('stage-done',i<which)})}
function clear(){stop();stepIndex=-1;truthShown=false;$('truthDetails').hidden=true;$('truthDetails').replaceChildren();for(const id of ['replayPanel','missionPanel','visualPanel','requirementsPanel','oraclePanel'])$(id).hidden=true;stext('chResult','—');stext('chWarningTag','Monitoring: awaiting evidence');stext('chExecuted','—');stext('chCause','—');stext('chTime','—');stage(-1);mission.set(null,{});mission.setOracle(null,false);mission.focus(null)}
function el(tag,text,cls){let x=document.createElement(tag);if(text!=null)x.textContent=text;if(cls)x.className=cls;return x}
function checkPill(k,v){const x=el('span',k+' · '+(v===true?'PASS':v===false?'FAIL':'NOT CHECKED'),v===true?'ok':v===false?'bad':'');return x}
function tinyCanvas(id,items,prop,color,seconds){const canvas=$(id),width=canvas.clientWidth||390,height=230,dpr=window.devicePixelRatio||1;canvas.width=Math.round(width*dpr);canvas.height=height*dpr;const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);ctx.font='11px sans-serif';const values=items.filter(d=>Number.isFinite(d[prop]));if(!values.length){ctx.fillStyle='#8cb2c4';ctx.fillText('Awaiting sampled telemetry',15,55);return}const ymin=Math.min(...values.map(d=>d[prop])),ymax=Math.max(...values.map(d=>d[prop]));let lo=ymin-(ymax-ymin||.5)*.2,hi=ymax+(ymax-ymin||.5)*.2;const x=t=>42+Math.max(0,t)/Math.max(60,seconds)*(width-58),y=v=>height-27-(v-lo)/(hi-lo)*(height-54);for(let i=0;i<4;i++){let yy=18+(height-45)*i/3;ctx.strokeStyle='#2c4960';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(42,yy);ctx.lineTo(width-15,yy);ctx.stroke();ctx.fillStyle='#8faec4';ctx.fillText((hi-(hi-lo)*i/3).toFixed(2),2,yy+4)}ctx.fillText('0 m',42,height-5);ctx.fillText((seconds/60).toFixed(0)+' m',width-45,height-5);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();values.filter(d=>d.time_s<=seconds).forEach((d,i)=>i?ctx.lineTo(x(d.time_s),y(d[prop])):ctx.moveTo(x(d.time_s),y(d[prop])));ctx.stroke()}
function showBelief(record){const b=record?.posterior||Object.fromEntries(Object.keys(current.posterior||{}).map(k=>[k,1/Object.keys(current.posterior||{}).length]));const sorted=Object.entries(b).sort((a,b)=>b[1]-a[1]).slice(0,6);$('beliefBars').replaceChildren();for(const [h,v] of sorted){const row=el('div',null,'belief-row');row.append(el('span',HYP[h]||h));const track=el('div',null,'belief-track'),bar=el('i');bar.style.width=Math.max(1,v*100)+'%';track.append(bar);row.append(track,el('b',(v*100).toFixed(1)+'%'));$('beliefBars').append(row)}}
function stepTo(index){if(!current)return;const records=current.evidence||[];stepIndex=Math.max(-1,Math.min(index,records.length-1));$('replaySlider').value=String(stepIndex+1);$('replaySlider').max=String(records.length);
 const rec=records[stepIndex];const cutoff=rec?.end_s||0;const stageId=stepIndex<0?-1:Math.min(4,2+(stepIndex%3));stage(stageId);
 stext('chTime',fmt(cutoff));stext('chExecuted',stepIndex+1);stext('chCause',rec?HYP[Object.keys(rec.posterior||{}).sort((a,b)=>rec.posterior[b]-rec.posterior[a])[0]]||'Unknown':'Awaiting evidence');
 stext('stepClock',fmt(cutoff));stext('activeProcedure',rec?`${rec.test_id} · ${rec.test_name}`:'Starting conditions');stext('activeReason',rec?`${POLICY[current.meta.policy]} · ${COVERAGE_EXPLANATION[rec.decision?.coverage_guard]||rec.decision?.reason||'Recorded verification decision'} · ${fmt(rec.start_s)}–${fmt(rec.end_s)}`:'Press Play to replay the completed verification campaign.');
 $('activeChecks').replaceChildren();const planText=rec?.decision?.planned_sequence?.length?' Planned sequence (before this test): '+rec.decision.planned_sequence.join(' → ')+'. ':rec?.decision?.scheduler_mode==='short_budget_greedy_fallback'?' Short-budget greedy fallback; full sequence search is disabled for 35-minute or shorter campaigns. ':'';const warnings=planText+(rec?.test_window_monitor?.comms_warning?'Communication loss exceeded 10% during this test. ':'')+(rec?.decision?.warning?'Pre-test anomaly alert. ':'')+(rec?.decision?.forecast_voltage_risk?'Voltage forecast indicated possible limit crossing. ':'')+(rec?.decision?.forecast_temperature_risk?'Thermal forecast indicated possible limit crossing. ':'');stext('decisionSignals',warnings||'No active monitor warning was attached to this test. This does not prove the subsystem is healthy.');if(rec)for(const [req,result] of Object.entries(rec.checks||{}))$('activeChecks').append(checkPill(req,result));
 const passed=records.slice(0,stepIndex+1);const failure=passed.some(x=>x.status==='FAIL');const observedAlerts=(current?.weak_fault_analysis?.warning_events||[]).filter(x=>x.time_s<=records[stepIndex]?.end_s);const weak=observedAlerts.length?observedAlerts.at(-1):null;
 stext('chResult',failure?'Requirement failure':weak?'No failure · early warning':'No verified failure');
 stext('chWarningTag',weak?`Monitoring: ${weak.subsystem} deviation at ${fmt(weak.time_s)} (advisory)`:'Monitoring: no observed early warning');$('challengeStatus').classList.toggle('fail',failure);stext('challengeStatus',failure?'FAILED CHECK':stepIndex<0?'READY':'REPLAYING');
 document.querySelectorAll('#replayRibbon button').forEach((b,i)=>b.classList.toggle('selected',i===stepIndex));
 const checked={};for(const record of passed)for(const [req,val] of Object.entries(record.checks||{})){if(val!==null)checked[req]=val}
 $('requirementMap').replaceChildren();const all=new Set(records.flatMap(x=>Object.keys(x.checks||{})));for(const name of [...all].sort()){const v=checked[name];$('requirementMap').append(el('span',name+' · '+(v===false?'FAIL':v===true?'PASS':'unchecked'),v===false?'failed':v===true?'passed':'unchecked'))}
 for(const sys of SUBSYSTEM){const x=document.querySelector(`[data-system="${sys}"]`);if(!x)continue;const matching=passed.filter(r=>r.subsystem===sys);const failed=matching.some(r=>r.status==='FAIL');x.className='subsystem-card '+(failed?'bad':matching.length?'ok':'');if(rec?.subsystem===sys)x.classList.add('active');x.querySelector('small').textContent=failed?'CHECK FAILED':matching.length?`${matching.length} procedure(s) checked`:'NOT YET CHECKED'}
 updateCharts(cutoff);showBelief(rec);
 mission.focus(rec?.subsystem||null);mission.set(rec,rec?.posterior||{});
 stext('missionFlag',rec?(rec.status==='FAIL'?'REQUIREMENT FAILURE':rec.status==='PASS'?'VERIFIED CHECK':'INCONCLUSIVE'):'STARTING STATE');
 stext('missionActive',rec?`${rec.test_id} · ${rec.test_name} — ${rec.status}`:'Ready to replay');
 const obs=(current.observations||[]).filter(x=>x.time_s<=cutoff).at(-1);$('measurementPanel').replaceChildren();if(obs){for(const key of ['bus_voltage_v','bus_current_a','battery_soc_pct','temperature_c','redundant_temperature_c','packet_loss_fraction']){const spec=SIGNALS[key];if(!spec)continue;const box=el('div',null,'reading-tile');box.append(el('small',spec[0]),el('strong',Number(obs[key]).toFixed(key==='packet_loss_fraction'?3:2)+' '+spec[1]));$('measurementPanel').append(box)}}
 const interpretation=rec?.status==='FAIL'?'A completed check found a requirement violation. The inferred fault hypothesis is not proven.':rec?'Checks completed: '+Object.keys(checked).length+' distinct requirements. Continue replaying for later evidence.':'Simulation completed on the server. This animation replays recorded decisions.';stext('chInterpret',interpretation);if(window.SATVV_INTERPRET)window.SATVV_INTERPRET.step(current,cutoff,rec);
}
function buildResult(result){current=result;clear();for(const id of ['replayPanel','missionPanel','visualPanel','requirementsPanel','oraclePanel'])$(id).hidden=false;stext('challengeTitle',`${result.meta.experiment_mode==='manual'?'CONFIGURED: '+(HYP[result.meta.scenario]||result.meta.scenario).toUpperCase():result.meta.challenge_level.toUpperCase()+' · '+(result.meta.challenge_intensity==='high_impact'?'HIGH-IMPACT':'EXPLORATORY')} · SEED ${result.meta.seed}`);
$('subsystemGrid').replaceChildren();const icon={EPS:'M3 10h18M5 6h14v12H5zM9 3v3m6-3v3',THERMAL:'M12 3a2 2 0 0 0-2 2v10a4 4 0 1 0 4 0V5a2 2 0 0 0-2-2zM12 9v9',OBC:'M6 6h12v12H6zM9 9h6v6H9zM9 2v4m6-4v4m-6 12v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4',COMMS:'M2 8a15 15 0 0 1 20 0M5 11a10 10 0 0 1 14 0M8 14a5 5 0 0 1 8 0M12 18v3',PAYLOAD:'M4 6l8-4 8 4v12l-8 4-8-4zM4 6l8 5 8-5M12 11v11',ADCS:'M12 2v4m0 12v4M2 12h4m12 0h4M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 10v4m-2-2h4'};
 for(const subsystem of SUBSYSTEM){const node=el('div',null,'subsystem-card');node.dataset.system=subsystem;
 const symbol=el('span',null,'subsystem-symbol');symbol.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+icon[subsystem]+'"/></svg>';node.append(symbol,el('b',subsystem),el('small','NOT YET CHECKED'));$('subsystemGrid').append(node)}
 $('revealTruth').hidden=result.meta.experiment_mode==='manual';stext('truthNote',result.meta.experiment_mode==='manual'?'You chose this scenario in advance. Verification algorithms only receive measured telemetry and evidence.':'Hidden oracle available after the run; it was not exposed to the scheduler.');
 if(window.SATVV_INTERPRET)window.SATVV_INTERPRET.result(result);
$('replayRibbon').replaceChildren();(result.evidence||[]).forEach((rec,i)=>{const button=el('button',`${fmt(rec.end_s)} ${rec.test_id} · ${rec.status}${rec.test_window_monitor?.comms_warning?' ⚠':''}`,rec.status==='FAIL'?'has-fail':'');button.onclick=()=>{stop();stepTo(i)};$('replayRibbon').append(button)});
exposureSummary(result);stepTo(-1);$('startChallenge').disabled=false;$('compareChallenge').disabled=false;}
async function run(){const s=settings();let ticket=++requestSerial;clear();current=null;stext('challengeError','');$('startChallenge').disabled=true;$('compareChallenge').disabled=true;stext('challengeTitle','Running a simulated verification campaign…');stext('challengeStatus','COMPUTING');$('challengeStatus').classList.add('challenge-loading');stage(0);startComputing();try{const result=await post(s);if(ticket!==requestSerial)return;if(result.meta.policy!==s.policy||result.evidence.some(e=>e.decision.selected_policy!==s.policy))throw Error('Policy-evidence mismatch');buildResult(result)}catch(e){stext('challengeError',e.message);stext('challengeStatus','ERROR');$('startChallenge').disabled=false}finally{stopComputing();$('challengeStatus').classList.remove('challenge-loading')}}
async function compare(){
 const s=settings(); const ticket=++requestSerial;
 const main=$('compareNow'),sidebar=$('compareChallenge');
 for(const btn of [main,sidebar]){btn.disabled=true;btn.setAttribute('aria-busy','true');}
 $('compareActivity').hidden=false;
 $('comparisonBody').replaceChildren();$('comparisonChart').getContext('2d').clearRect(0,0,$('comparisonChart').width,$('comparisonChart').height);
 $('comparePrompt').textContent=`Running ${s.mode==='manual'?'manual scenario '+s.scenario:s.intensity+' '+s.difficulty+' challenge'} · seed ${s.seed} · ${s.budget_min} min`;
 const rows=[],all=Object.keys(POLICY);
 try{
  for(let i=0;i<all.length;i++){
   const policy=all[i];stext('compareStatus',`Running ${i+1}/${all.length}: ${POLICY[policy]}…`);
   // Every policy receives a separate, reproducible simulator run.
   const result=await post({...s,policy});if(ticket!==requestSerial)return;
   const weakEvents=result.weak_fault_analysis?.warning_events||[];rows.push({policy:POLICY[policy],detected:result.detected,seconds:result.detection_s,firstWarning:weakEvents[0]?.time_s??null});
   renderComparisonChart(rows,s.budget_min);
   const tr=el('tr');for(const value of [POLICY[policy],result.detected?'Yes':'No',weakEvents.length?'Advisory':'None',fmt(weakEvents[0]?.time_s),fmt(result.spent_s),result.tests_run,HYP[result.estimated_cause]||result.estimated_cause,result.diagnosis_match==null?'N/A':result.diagnosis_match?'Partially':'No'])tr.append(el('td',String(value)));
   $('comparisonBody').append(tr);
  }
  stext('compareStatus','All five independent comparisons complete');
  $('comparePrompt').textContent=`Completed ${rows.length} policies on the same ${s.mode} initial conditions. Mint bars end at a verified failure; amber dots mark the time of an advisory warning only. Warnings are not verification FAIL results.`;
 }catch(e){stext('compareStatus','Comparison stopped');stext('comparePrompt',`Comparison error: ${e.message}`);stext('challengeError',e.message)}
 finally{$('compareActivity').hidden=true;for(const btn of [main,sidebar]){btn.disabled=false;btn.removeAttribute('aria-busy');}}
}
// Visual semantics: a mint duration bar ends at a VERIFIED requirement failure;
// an amber point marks the INSTANT of an advisory-only warning. An amber point
// is not a duration bar and must never be painted beneath the warning label.
function renderComparisonChart(rows, budget) {
  const canvas = $('comparisonChart');
  const width = Math.max(320, canvas.clientWidth || 650);
  const height = 230;
  const dpr = Math.min(3, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const left = width < 650 ? 130 : 187;
  const statusWidth = width < 650 ? 113 : 151;
  const right = 14;
  const timelineWidth = Math.max(50, width - left - statusWidth - right - 13);
  const statusX = left + timelineWidth + 13;
  const timeLimit = Math.max(1, Number(budget) || 1);
  const at = seconds => left + Math.min(1, Math.max(0, (Number(seconds) || 0) / 60 / timeLimit)) * timelineWidth;
  const amber = '#f0b767';
  const mint = '#6ae3bd';
  const muted = '#9eb6c6';
  const rowGap = 31;
  const top = 43;

  ctx.textBaseline = 'middle';
  ctx.font = '600 11px sans-serif';
  ctx.fillStyle = '#a9cbd8';
  ctx.fillText(width < 650 ? 'FAILURE / WARNING TIMES' : 'VERIFIED FAILURE (MINT) · EARLY WARNING TIME (AMBER)', 11, 17);

  function shorten(text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) return text;
    let result = text;
    while (result.length > 1 && ctx.measureText(result + '…').width > maxWidth) result = result.slice(0, -1);
    return result + '…';
  }

  rows.forEach((row, i) => {
    const cy = top + i * rowGap;
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#c1d1da';
    ctx.fillText(shorten(row.policy, left - 15), 10, cy);

    // Neutral time track: warnings are POINTS, not filled time intervals.
    ctx.fillStyle = '#173446';
    ctx.fillRect(left, cy - 5, timelineWidth, 10);
    ctx.fillStyle = '#345369';
    ctx.fillRect(left, cy - 1, timelineWidth, 2);

    const warning = Number.isFinite(Number(row.firstWarning)) && row.firstWarning != null;
    const failure = row.detected && Number.isFinite(Number(row.seconds)) && row.seconds != null;
    if (failure) {
      const x = at(row.seconds);
      ctx.fillStyle = mint;
      ctx.fillRect(left, cy - 4, Math.max(2, x - left), 8);
      ctx.fillStyle = mint;
      ctx.font = '600 11px sans-serif';
      ctx.fillText('FAIL · ' + (row.seconds / 60).toFixed(1) + 'm', statusX, cy);
    } else if (warning) {
      const x = at(row.firstWarning);
      // Short tick + outlined dot. Never draw an amber bar from 0 to x.
      ctx.strokeStyle = amber;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, cy - 8);
      ctx.lineTo(x, cy + 8);
      ctx.stroke();
      ctx.fillStyle = '#092031';
      ctx.beginPath();
      ctx.arc(x, cy, 5, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = amber;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = amber;
      ctx.font = '600 11px sans-serif';
      ctx.fillText('WARN · ' + (row.firstWarning / 60).toFixed(1) + 'm', statusX, cy);
    } else {
      ctx.fillStyle = muted;
      ctx.font = '11px sans-serif';
      ctx.fillText('No event', statusX, cy);
    }
  });

  // Shared time axis makes the amber dot's position interpretable.
  const axisY = 207;
  ctx.fillStyle = muted;
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('0 min', left, axisY);
  ctx.textAlign = 'center';
  ctx.fillText((timeLimit / 2).toFixed(0) + ' min', left + timelineWidth / 2, axisY);
  ctx.textAlign = 'right';
  ctx.fillText(timeLimit.toFixed(0) + ' min', left + timelineWidth, axisY);
  ctx.textAlign = 'left';
}
function truth(){if(!current)return;if(current.meta?.experiment_mode==='manual'){stext('truthNote','Manual scenario selected by you; there is no hidden random ground truth.');return}truthShown=!truthShown;$('truthDetails').hidden=!truthShown;$('faultExposure').hidden=!truthShown;mission.setOracle(current.oracle_after_run,truthShown);if(!truthShown){document.querySelectorAll('.truth-marker').forEach(n=>n.remove());stext('revealTruth','Reveal injected fault record');return}stext('revealTruth','Hide ground truth');const root=$('truthDetails');root.replaceChildren();const oracle=current.oracle_after_run;root.append(el('p',oracle.healthy?'This generated case was healthy.':`${oracle.fault_count} injected fault episode(s); the controller never received these labels.`));for(const fault of oracle.faults){const first=[...$('replayRibbon').querySelectorAll('button')].find(b=>{const match=b.textContent.match(/^([\d.]+) min/);return match&&parseFloat(match[1])*60>=fault.onset_s;});if(first){const marker=el('span','⚑ '+fmt(fault.onset_s)+' '+fault.mechanism.replaceAll('_',' '),'truth-marker');first.before(marker)}const text=`${fault.mechanism.replaceAll('_',' ')} · onset ${fmt(fault.onset_s)} · until ${fmt(fault.end_s)} · severity ${fault.severity}`;root.append(el('div',text,'oracle-fault'))}root.append(el('p',current.diagnosis_match_note,'help'))}
function invalidateComparison(){const tbody=$('comparisonBody');if(tbody)tbody.replaceChildren();stext('comparePrompt','Settings changed. Run the five methods again to compare the new conditions.');}
function updateExperimentMode(){const manual=$('experimentMode').value==='manual';$('manualControls').hidden=!manual;$('randomControls').hidden=manual;$('reroll').hidden=manual;$('startChallenge').querySelector('span:last-child').textContent=manual?'Run selected scenario':'Generate & run challenge'}
 $('experimentMode').addEventListener('change',()=>{clear();invalidateComparison();updateExperimentMode()});updateExperimentMode();
 for(const [range,label,suffix] of [['manualSeverity','manualSeverityLabel','×'],['manualSoc','manualSocLabel','%']])$(range).addEventListener('input',()=>stext(label,$(range).value+suffix));
 $('startChallenge').onclick=run;$('reroll').onclick=()=>{$('chSeed').value=String((Number($('chSeed').value)+1)%1000001);clear();invalidateComparison()};$('compareChallenge').onclick=()=>{document.getElementById('compare-workspace').scrollIntoView({behavior:'smooth',block:'start'});compare()};$('compareNow').onclick=compare;$('revealTruth').onclick=truth;$('chBudget').oninput=()=>stext('budgetLabel',$('chBudget').value+' min');$('playPause').onclick=()=>{if(!current)return;if(timer){stop();return}stext('playPause','Ⅱ Pause');if(stepIndex===(current.evidence||[]).length-1)stepTo(-1);timer=setInterval(()=>{if(stepIndex===(current.evidence||[]).length-1){stop();stage(4);stext('challengeStatus','REPLAY COMPLETE');return}stepTo(stepIndex+1)},650)};
$('backStep').onclick=()=>{stop();stepTo(stepIndex-1)};$('forwardStep').onclick=()=>{stop();stepTo(stepIndex+1)};$('replaySlider').oninput=()=>{stop();stepTo(Number($('replaySlider').value)-1)};
for(const input of ['experimentMode','difficulty','intensity','chBudget','chSeed','chPolicy','manualScenario','manualOnset','manualSeverity','manualSoc','manualEclipse','manualHorizon','manualDetector'])$(input).addEventListener('change',()=>{invalidateComparison();if(current)stext('challengeError','Settings changed. Rerun for a single-policy replay; comparison uses the current settings.')});

for(const [id,initial] of [['leftSignal','bus_voltage_v'],['rightSignal','temperature_c']]){
 const selector=$(id);for(const [key,[name,unit]] of Object.entries(SIGNALS)){const o=document.createElement('option');o.value=key;o.textContent=`${name} (${unit})`;selector.append(o)}selector.value=initial;selector.onchange=()=>{if(current){updateCharts(current.evidence?.[stepIndex]?.end_s||0);if(window.SATVV_INTERPRET)window.SATVV_INTERPRET.step(current,current.evidence?.[stepIndex]?.end_s||0,current.evidence?.[stepIndex]);}};
}

$('missionLayout').onchange=()=>{const layout=$('missionLayout').value;$('missionPanel').classList.toggle('mission-data-view',layout==='data');$('visualPanel').classList.toggle('mission-hide-visual',layout==='model');$('missionPanel').classList.toggle('mission-wide',layout==='model');mission.draw();};
$('missionFollow').onchange=()=>{mission.follow=$('missionFollow').checked;};
$('missionReset').onclick=()=>mission.reset();
