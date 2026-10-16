"use strict";
const data={20:[22.2,61.1,77.8,50,72.2],26:[22.2,72.2,77.8,83.3,77.8]};
const names=['Fixed-order','Temporal adaptive','Bayesian info gain','ML-ranked','Predictive active'];
const sel=document.getElementById('benchmarkBudget'),host=document.getElementById('benchmarkBars');
function renderBench(){if(!sel||!host)return;host.replaceChildren();data[sel.value].forEach((val,i)=>{const row=document.createElement('div');row.className='benchmark-row'+(i===4?' highlight':'');const n=document.createElement('span');n.textContent=names[i];const track=document.createElement('div');track.className='benchmark-track';const fill=document.createElement('div');fill.className='benchmark-fill';fill.style.width=val+'%';track.append(fill);const v=document.createElement('strong');v.textContent=val.toFixed(1)+'%';row.append(n,track,v);host.append(row);});host.setAttribute('aria-label','Synthetic detection rates with '+sel.value+' minute budget: '+names.map((n,i)=>n+' '+data[sel.value][i]+'%').join('; '));}
if(sel)sel.addEventListener('change',renderBench);renderBench();
