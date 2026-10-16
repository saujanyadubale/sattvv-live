/* SAT-V&V v1.0 beta: optional high-fidelity WebGL scene.
 * Experimental geometry is a visualization, not a physical spacecraft model or a fault-localization claim.
 * A verified NASA CubeSat GLB can be loaded only over a network or through the file control.
 * If the renderer CDN is unavailable, the bundled offline v0.9.9 canvas remains functional.
 */
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {DRACOLoader} from 'three/addons/loaders/DRACOLoader.js';
const parent = document.getElementById('missionWrap');
const oldCanvas = document.getElementById('missionCanvas');
if (!parent || !oldCanvas || !window.SATVV_MissionView) throw Error('Mission replay not initialized');
const renderer = new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.20;
window.SATVV_BETA_RENDER_READY=true;renderer.domElement.className='mission-webgl';renderer.domElement.setAttribute('aria-label','Interactive 3D spacecraft with mapped diagnostic regions');
parent.prepend(renderer.domElement);
const scene=new THREE.Scene();
// Transparent canvas lets the static, CSS-only deep starfield sit behind every model.
// No stars are rendered in front of the spacecraft.
scene.background=null;scene.fog=new THREE.FogExp2('#071522',.018);
const camera=new THREE.PerspectiveCamera(37,1,.06,200);camera.position.set(9.6,5.7,16.8);
const target=new THREE.Vector3(1.15,.05,0);
scene.add(new THREE.HemisphereLight(0xb6e4ff,0x15213a,2.1));
const sun=new THREE.DirectionalLight(0xd8ebff,4.1);sun.position.set(-6,8,9);scene.add(sun);
const rim=new THREE.DirectionalLight(0x3eb8d3,3.5);rim.position.set(6,0,-6);scene.add(rim);
const warm=new THREE.PointLight(0xe4ab72,7,18);warm.position.set(3,2,-3);scene.add(warm);
const satin=new THREE.MeshStandardMaterial({color:0x8eabc0,metalness:.85,roughness:.24});
const frame=new THREE.MeshStandardMaterial({color:0x40546a,metalness:.94,roughness:.27});
const gold=new THREE.MeshStandardMaterial({color:0xd8a04a,metalness:.72,roughness:.31});
const dark=new THREE.MeshStandardMaterial({color:0x152b41,metalness:.58,roughness:.35});
const cell=new THREE.MeshPhysicalMaterial({color:0x194a7e,metalness:.54,roughness:.24,clearcoat:.85,clearcoatRoughness:.11});
const ant=new THREE.MeshStandardMaterial({color:0xb6cad6,metalness:.91,roughness:.26});
const craftGroup=new THREE.Group();scene.add(craftGroup);
function addBox(root,w,h,d,x,y,z,mat){let o=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);o.position.set(x,y,z);root.add(o);return o}
function beam(root,a,b,r,mat){let v1=new THREE.Vector3(...a),v2=new THREE.Vector3(...b),v=v2.clone().sub(v1);const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,v.length(),12),mat);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.clone().normalize());mesh.position.copy(v1).add(v2).multiplyScalar(.5);root.add(mesh);return mesh}
function buildConceptual(){let g=new THREE.Group();
 addBox(g,1.7,2.20,1.55,0,0,0,satin);
 for(let y of [-.99,.99])for(let x of [-.78,.78]){beam(g,[x,y,-.76],[x,y,.76],.052,frame)}
 for(let z of [-.77,.77])for(let x of [-.76,.76])beam(g,[x,-1.07,z],[x,1.07,z],.043,frame);
 for(let y of [-.9,-.33,.3,.88])for(let z of [-.78,.78]) beam(g,[-.81,y,z],[.81,y,z],.032,frame);
 for(let side of [-1,1]){
   const p=new THREE.Group();p.position.set(side*2.42,.20,0);
   addBox(p,2.95,.055,1.70,0,0,0,frame);
   for(let i=0;i<8;i++)for(let j=0;j<4;j++)addBox(p,.323,.065,.341,-1.29+i*.369,.017,-.62+j*.412,cell);
   for(let x of [-1.49,1.49])beam(p,[x,-.01,-.85],[x,-.01,.85],.045,satin);
   g.add(p);beam(g,[side*.86,.18,0],[side*.96,.18,0],.04,ant);
 }
 addBox(g,.95,.48,.16,0,.28,.855,dark);
 addBox(g,.8,.55,.12,.04,-.57,.842,gold);
 for(let i=0;i<7;i++)addBox(g,.06,.20,.025,-.36+i*.12,.33,.945,satin);
 for(let i=0;i<5;i++)addBox(g,1.25,.026,.028,0,-.85+i*.11,.789,frame);
 const dish=new THREE.Mesh(new THREE.SphereGeometry(.31,24,16,0,Math.PI*2,0,Math.PI*.42),ant);dish.position.set(.55,1.28,.42);dish.rotation.x=Math.PI;g.add(dish);
 beam(g,[.56,1.02,.38],[.56,1.7,.50],.027,ant);
 for(let x of [-.5,.5])for(let z of [-.5,.5])addBox(g,.18,.12,.18,x,1.16,z,gold);
 const l=new THREE.Mesh(new THREE.TorusGeometry(.24,.014,6,32),new THREE.MeshBasicMaterial({color:0x45c8d4}));l.position.set(-.5,-.55,.855);g.add(l);
 return g;
}
function buildCubeSat(){
 // A clearly different, bundled 6U-style CubeSat concept, not a NASA flight model.
 const g=new THREE.Group();
 const bodyMat=new THREE.MeshStandardMaterial({color:0x728eab,metalness:.78,roughness:.27});
 const mli=new THREE.MeshStandardMaterial({color:0xc8994e,metalness:.78,roughness:.35});
 const blue=new THREE.MeshPhysicalMaterial({color:0x183d80,metalness:.39,roughness:.29,clearcoat:.7});
 const metal=new THREE.MeshStandardMaterial({color:0x364a61,metalness:.82,roughness:.32});
 addBox(g,1.50,2.25,1.28,0,0,0,bodyMat);
 // Distinct compact bus: solar cells mounted ON the spacecraft, no long deployed wings.
 for(let side of [-1,1]){
   for(let col=0;col<2;col++)for(let row=0;row<5;row++){
     let c=addBox(g,.028,.335,.49,side*.77,-.80+row*.395,-.28+col*.57,blue);
     c.material=blue;
   }
   for(let y of [-1.12,1.12])beam(g,[side*.76,y,-.67],[side*.76,y,.67],.045,metal);
 }
 // Front avionics/service panel + payload aperture.
 addBox(g,1.28,1.66,.08,0,-.19,.67,mli);
 addBox(g,.91,.36,.10,0,.68,.74,metal);
 for(let i=0;i<7;i++)addBox(g,.067,.20,.016,-.38+i*.13,.68,.81,bodyMat);
 const lens=new THREE.Mesh(new THREE.CylinderGeometry(.27,.27,.19,36),metal);
 lens.rotation.x=Math.PI/2;lens.position.set(.15,-.55,.80);g.add(lens);
 const darkLens=new THREE.Mesh(new THREE.CircleGeometry(.18,32),new THREE.MeshBasicMaterial({color:0x113454}));
 darkLens.position.set(.15,-.55,.92);g.add(darkLens);
 // Crossed monopole pair is visibly different from the large solar-array spacecraft.
 beam(g,[-.14,1.13,0],[-.52,2.04,.16],.025,ant);
 beam(g,[.14,1.13,0],[.58,1.76,.28],.019,ant);
 addBox(g,1.20,.085,1.10,0,1.17,0,metal);
 addBox(g,1.20,.085,1.10,0,-1.16,0,metal);
 return g;
}
function createGround(){
 // Mechanical Cassegrain-style ground terminal, drawn procedurally. Not a sourced antenna CAD model.
 const g=new THREE.Group();g.position.set(7.25,-2.42,-.8);g.scale.setScalar(.82);
 const porcelain=new THREE.MeshStandardMaterial({color:0xa4bbc9,metalness:.64,roughness:.32,side:THREE.DoubleSide});
 const ribs=new THREE.MeshStandardMaterial({color:0x547487,metalness:.77,roughness:.34});
 const composite=new THREE.MeshStandardMaterial({color:0x22394c,metalness:.42,roughness:.56});
 const rimMaterial=new THREE.MeshStandardMaterial({color:0xbfd5db,metalness:.83,roughness:.24});
 addBox(g,2.55,.16,1.8,0,-.88,0,composite);
 addBox(g,1.32,.12,1.21,0,-.74,0,ribs);
 addBox(g,.7,1.35,.65,0,-.01,0,porcelain);
 addBox(g,.98,.36,.9,0,.78,0,ribs);
 const azimuth=new THREE.Group();azimuth.position.set(0,.92,0);g.add(azimuth);
 // Two trunnions support a tilting dish, not a floating ellipse.
 for (let z of [-.58,.58]){
    addBox(azimuth,.19,.98,.20,0,.43,z,ribs);
    const axle=new THREE.Mesh(new THREE.CylinderGeometry(.21,.21,.15,22),composite);
    axle.rotation.x=Math.PI/2;axle.position.set(0,.90,z);azimuth.add(axle);
 }
 const mount=new THREE.Group();mount.position.set(0,1.00,0);azimuth.add(mount);
 // Paraboloid of revolution: a concave reflecting surface, with radial backing struts.
 const R=1.13,depth=.38,points=[];
 for(let i=0;i<=30;i++) {const r=R*i/30;points.push(new THREE.Vector2(r,depth*(r/R)*(r/R)));}
 const dish=new THREE.Mesh(new THREE.LatheGeometry(points,72),porcelain);
 dish.material.side=THREE.DoubleSide;dish.name='Ground station parabolic reflector';mount.add(dish);
 const lip=new THREE.Mesh(new THREE.TorusGeometry(R,.028,8,90),rimMaterial);lip.rotation.x=Math.PI/2;lip.position.y=depth;mount.add(lip);
 const back=new THREE.Mesh(new THREE.CylinderGeometry(.35,.48,.14,38),ribs);back.position.y=-.11;mount.add(back);
 for(let i=0;i<16;i++){
   let a=i*Math.PI/8;const out=[Math.cos(a)*R,depth,Math.sin(a)*R];
   beam(mount,[0,-.17,0],out,.017,ribs);
 }
 // Feed-support tripod and feedhorn accurately follow the dish boresight.
 for(let i=0;i<3;i++){let a=i*2*Math.PI/3;beam(mount,[R*.82*Math.cos(a),depth*.70,R*.82*Math.sin(a)],[0,.86,0],.017,rimMaterial);}
 const horn=new THREE.Mesh(new THREE.CylinderGeometry(.08,.045,.22,20),composite);horn.position.y=.86;mount.add(horn);
 const radome=new THREE.Mesh(new THREE.SphereGeometry(.065,16,10),gold);radome.position.y=.98;mount.add(radome);
 // Model the dish facing roughly toward the satellite, not toward the camera.
 const aim=new THREE.Vector3(-.9,.55,.25).normalize();
 mount.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),aim);
 // Receiver enclosure, cable run, and grounded pad for visual clarity.
 addBox(g,1.24,.62,.84,-1.07,-.44,.82,composite);
 addBox(g,1.12,.08,.72,-1.07,-.11,.82,porcelain);
 beam(g,[-.45,-.52,.22],[-.93,-.50,.65],.037,ribs);
 // A subtle circular ground-terminal service ring.
 const service=new THREE.Mesh(new THREE.TorusGeometry(1.69,.015,6,72),new THREE.MeshBasicMaterial({color:0x35647c,transparent:true,opacity:.40}));service.rotation.x=-Math.PI/2;service.position.y=-.94;g.add(service);
 return g;
}
scene.add(createGround());
// The deep-star background is now a static CSS texture behind the transparent WebGL canvas.
const anchors={EPS:new THREE.Vector3(-.69,.22,.76),THERMAL:new THREE.Vector3(.58,.42,.76),OBC:new THREE.Vector3(0,-.05,.91),COMMS:new THREE.Vector3(.55,1.28,.4),PAYLOAD:new THREE.Vector3(.03,-.58,.93),ADCS:new THREE.Vector3(-.5,-.55,.85)};
const HYP={resistance_ramp:'EPS',intermittent_resistance:'EPS',sensor_drift:'THERMAL',heater_fault:'THERMAL',radio_burst:'COMMS',adcs_gyro_bias:'ADCS',adcs_wheel_weak:'ADCS',adcs_star_dropout:'ADCS'};
const anchorProfiles={
 conceptual:{EPS:[-.69,.22,.76],THERMAL:[.58,.42,.76],OBC:[0,-.05,.91],COMMS:[.55,1.28,.4],PAYLOAD:[.03,-.58,.93],ADCS:[-.5,-.55,.85]},
 cubesat:{EPS:[-.75,.21,.52],THERMAL:[.62,.4,.67],OBC:[0,.66,.86],COMMS:[.1,1.53,.1],PAYLOAD:[.15,-.57,.95],ADCS:[-.56,-.61,.68]}
};
function anchorProfile(kind){for(const [key,xyz] of Object.entries(anchorProfiles[kind]||anchorProfiles.conceptual)){anchors[key].set(...xyz)}
 for(const obj of hotspot||[])obj.ring.position.copy(anchors[obj.name]);}
let active='',record=null,hyp={},truth=[],reveal=false,chosenAsset='conceptual',currentModel=null;
let labelMode='focus';
const hot=new THREE.Group();scene.add(hot);
const hud=document.createElement('div');hud.className='mission-hotspots';hud.setAttribute('aria-label','Subsystem hotspots');parent.append(hud);
const modeSelect=document.getElementById('missionLabelMode');if(modeSelect)modeSelect.addEventListener('change',()=>{labelMode=modeSelect.value;statusUpdate()});
const markerLabels={};for(const name of ['EPS','THERMAL','OBC','COMMS','PAYLOAD','ADCS']){
 const label=document.createElement('button');label.type='button';label.className='mission-hotspot';label.textContent=name;
 label.title=`Focus ${name} modeled region`;label.addEventListener('click',()=>{target.copy(anchors[name]);});hud.append(label);markerLabels[name]=label;
}
const hotspot=[];for(let [name,pos] of Object.entries(anchors)){
 const material=new THREE.MeshBasicMaterial({color:0x59b9c4,transparent:true,opacity:.48,depthTest:false});
 const ring=new THREE.Mesh(new THREE.TorusGeometry(.22,.011,6,48),material);ring.position.copy(pos);ring.renderOrder=30;hot.add(ring);hotspot.push({name,ring});
}
const geo=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(1.2,1.65,0),new THREE.Vector3(6.65,-.75,.1)]);
const linkMat=new THREE.LineDashedMaterial({color:0x76e8f7,dashSize:.16,gapSize:.11,transparent:true,opacity:0.75});const link=new THREE.Line(geo,linkMat);link.computeLineDistances();scene.add(link);
function renderModel(obj){if(currentModel)craftGroup.remove(currentModel);currentModel=obj;craftGroup.add(obj)}
renderModel(buildConceptual());
function setStatus(s){const x=document.getElementById('missionAssetStatus');if(x)x.textContent=s}
function statusUpdate(){for(let {name,ring} of hotspot){let fail=record?.status==='FAIL'&&active===name;const top=Object.entries(hyp||{}).filter(([k])=>k!=='healthy').sort((a,b)=>b[1]-a[1])[0];let suspect=top&&top[1]>=.25&&HYP[top[0]]===name;
 const injected=reveal&&truth.some(f=>HYP[f.mechanism]===name&&f.onset_s<=(record?.end_s||0)&&(record?.end_s||0)<f.end_s);
 ring.material.color.set(injected?0xeb75bc:fail?0xff7781:active===name?0x57e8c6:suspect?0xffb56e:0x4b94a8);
 ring.material.opacity=(injected||fail||active===name||suspect)?1:.13;ring.scale.setScalar(fail?1.45:injected?1.25:active===name?1.14:1);
 const label=markerLabels[name];if(label){label.classList.toggle('active',active===name);label.classList.toggle('failed',fail);label.classList.toggle('injected',!!injected)}
 }
 link.visible=active==='COMMS';link.material.color.set(record?.status==='FAIL'?0xff8888:0x64e6ed);
}
async function loadCustom(url, label='Custom GLB'){setStatus(`Loading ${label}…`);if(assetPicker)assetPicker.disabled=true;try{
 const loader=new GLTFLoader();
 const draco=new DRACOLoader();draco.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.166.1/examples/jsm/libs/draco/');
 loader.setDRACOLoader(draco);const gltf=await loader.loadAsync(url);const m=gltf.scene;const bounds=new THREE.Box3().setFromObject(m);const size=new THREE.Vector3();bounds.getSize(size);if(!Number.isFinite(size.length())||size.length()===0)throw Error('Empty geometry');
 const center=new THREE.Vector3();bounds.getCenter(center);const normalizedScale=2.65/Math.max(size.x,size.y,size.z);m.scale.multiplyScalar(normalizedScale);m.position.copy(center.multiplyScalar(-normalizedScale));
 renderModel(m);chosenAsset='custom';setStatus(`${label} loaded · conceptual diagnostic markers (not CAD-mapped)`);return true;
 }catch(e){setStatus(`${label} could not load (${String(e?.message||e).slice(0,115)}). Current model retained. Check the GLB file and optional online Draco decoder availability.`);return false;}
 finally {if(assetPicker)assetPicker.disabled=false;}
}
// NASA assets can be downloaded separately and imported as a local GLB; no broken remote selector is shown.
const assetPicker=document.getElementById('missionAsset');if(assetPicker)assetPicker.addEventListener('change',()=>{
 if(assetPicker.value==='custom'){setStatus('Custom GLB · imported geometry with conceptual subsystem markers');return;}
 if(assetPicker.value==='cubesat'){
   chosenAsset='cubesat';renderModel(buildCubeSat());anchorProfile('cubesat');
   setStatus('Compact 6U CubeSat · second bundled model, no external download required');
 }else{
   chosenAsset='conceptual';renderModel(buildConceptual());anchorProfile('conceptual');
   setStatus('Solar-array satellite · bundled conceptual geometry');
 }
 statusUpdate();
});
const upload=document.getElementById('missionGlbUpload');if(upload)upload.addEventListener('change',async()=>{const f=upload.files?.[0];if(!f)return;if(!f.name.toLowerCase().endsWith('.glb')||f.size===0||f.size>30*1024*1024){setStatus('Choose a nonempty .glb file no larger than 30 MB');return;}const header=new Uint8Array(await f.slice(0,4).arrayBuffer());if(header.length!==4||String.fromCharCode(...header)!=='glTF'){setStatus('Invalid GLB signature. Export a binary glTF 2.0 (.glb), not a renamed .gltf or .zip file.');return;}const u=URL.createObjectURL(f);try{const ok=await loadCustom(u,'Custom GLB');if(ok&&assetPicker){const option=assetPicker.querySelector('option[value="custom"]');if(option)option.hidden=false;assetPicker.value='custom';}}finally{URL.revokeObjectURL(u)}});
function applyRecord(newRecord,prior){record=newRecord;hyp=prior||{};active=newRecord?.subsystem||'';statusUpdate();}
function applyOracle(oracle,show){reveal=!!show;truth=show?(oracle?.faults||[]):[];statusUpdate()}
const proto=window.SATVV_MissionView.prototype;
const oldSet=proto.set,oldOracle=proto.setOracle,oldFocus=proto.focus,oldReset=proto.reset;
proto.set=function(r,p){oldSet.call(this,r,p);applyRecord(r,p)};
proto.setOracle=function(o,s){oldOracle.call(this,o,s);applyOracle(o,s)};
proto.focus=function(s){oldFocus.call(this,s);active=s||record?.subsystem||'';statusUpdate()};
proto.reset=function(){oldReset.call(this);camera.position.set(9.6,5.7,16.8);target.set(1.15,.05,0)};
proto.draw=function(){}; // WebGL is now responsible for visual updates; stop unnecessary fallback redraws.
const hiddenCanvas=oldCanvas;hiddenCanvas.style.opacity='0';hiddenCanvas.style.pointerEvents='none';
let pointer=null;renderer.domElement.addEventListener('pointerdown',e=>{pointer={x:e.clientX,y:e.clientY,theta:Math.atan2(camera.position.x,camera.position.z),height:camera.position.y};renderer.domElement.setPointerCapture(e.pointerId)});
renderer.domElement.addEventListener('pointermove',e=>{if(!pointer)return;let r=Math.hypot(camera.position.x-target.x,camera.position.z-target.z);let a=pointer.theta+(e.clientX-pointer.x)*.006;camera.position.x=target.x+r*Math.sin(a);camera.position.z=target.z+r*Math.cos(a);camera.position.y=Math.max(-.5,Math.min(10,pointer.height+(e.clientY-pointer.y)*.02));});
renderer.domElement.addEventListener('pointerup',()=>pointer=null);renderer.domElement.addEventListener('pointercancel',()=>pointer=null);
renderer.domElement.addEventListener('wheel',e=>{e.preventDefault();camera.position.sub(target).multiplyScalar(e.deltaY>0?1.08:.92).add(target);},{passive:false});
function loop(t){if(!document.hidden&&parent.clientWidth){const w=parent.clientWidth,h=parent.clientHeight;if(renderer.domElement.width!==Math.round(w*renderer.getPixelRatio())||renderer.domElement.height!==Math.round(h*renderer.getPixelRatio())){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()}
 if(record?.status==='FAIL'&&document.getElementById('missionFollow')?.checked){target.lerp(anchors[active]||new THREE.Vector3(),.02)}else target.lerp(new THREE.Vector3(1.15,.05,0),.016);
 camera.lookAt(target);
 if(active==='COMMS')link.material.dashOffset=-(t/1000)*.23;
 for(let q of hotspot){q.ring.lookAt(camera.position);if(q.name===active){q.ring.rotation.z=t/1800}}
 for(const [name,anchor] of Object.entries(anchors)){const pos=anchor.clone().project(camera),label=markerLabels[name];label.style.left=((pos.x+1)*50)+'%';label.style.top=((1-pos.y)*50)+'%';label.hidden=pos.z>1 || pos.z< -1 || labelMode==='none' || (labelMode==='focus' && !label.classList.contains('active') && !label.classList.contains('failed') && !label.classList.contains('injected'));}
 renderer.render(scene,camera);
 }requestAnimationFrame(loop)}
requestAnimationFrame(loop);
setStatus('Solar-array satellite · bundled model. Switch to Compact 6U CubeSat to see a second distinct geometry.');
