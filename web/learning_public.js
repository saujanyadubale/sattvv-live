"use strict";
const $ = id => document.getElementById(id);
function node(tag, content, cls) {const n=document.createElement(tag); if(cls)n.className=cls; if(content!==undefined)n.textContent=String(content);return n;}
(async()=>{
 try {const response=await fetch('/api/learning-public/status');const d=await response.json(); if(!response.ok)throw Error(d.error||'Unavailable');
 $('model-info').textContent=`Validated frozen model ${d.model_id} · holdout AUC ${d.validation_auc} · Brier ${d.validation_brier}. Training is disabled online.`;
 } catch(e) {$('model-info').textContent='Frozen model unavailable: '+e.message; $('run').disabled=true;}
})();
$('comparison').addEventListener('submit',async(e)=>{
 e.preventDefault();const btn=$('run');btn.disabled=true;$('output').hidden=true;$('status').textContent='Running two independent simulations; please wait…';
 const fd=new FormData(e.target);const payload={seed:Number(fd.get('seed')),budget_min:Number(fd.get('budget_min')),difficulty:fd.get('difficulty'),intensity:fd.get('intensity')};
 try {const response=await fetch('/api/learning-public/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');$('results').replaceChildren();$('trace').replaceChildren();
 for(const r of data.runs){const card=node('section',undefined,'result');card.append(node('h3',r.policy==='predictive_active'?'Original v1.0.2':'Learned + soft coverage + retesting'));
 card.append(node('div',r.detected?`${r.first_failure_min} min`:'Not verified','metric'));
 card.append(node('p',`${r.distinct_tests}/20 distinct tests · ${r.requirements_checked} requirements · Audit ${r.audit_passed?'passed':'FAILED'}`));$('results').append(card);
 for(const t of r.test_history){const tr=document.createElement('tr');for(const value of [r.policy==='predictive_active'?'Original':'Learned',`${t.start_min}–${t.end_min}`,t.id,t.status,t.selected_was_repeat?'Yes':'No',t.learned_score===null?'—':t.learned_score])tr.append(node('td',value));$('trace').append(tr)}
 }
 $('faults').textContent=JSON.stringify(data.injected_faults_revealed_after_run,null,2);$('output').hidden=false;$('status').textContent='Two simulations completed. No information was stored.';
 } catch(err){$('status').textContent='Could not complete comparison: '+err.message} finally {btn.disabled=false;}
});
