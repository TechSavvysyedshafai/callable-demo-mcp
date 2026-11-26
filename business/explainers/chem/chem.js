(function(){
'use strict';
const $ = id => document.getElementById(id);
const SHORT = location.hash === '#short';
const RECORD = location.hash === '#record' || SHORT;
if (SHORT) document.body.classList.add('short');

// ---------- chemistry ----------
// Kp (atm^-2) for N2 + 3H2 <=> 2NH3. Values from the Haber process table on Wikipedia (checked 26 Nov 2026);
// 400 °C value also in standard textbook problems. Interpolated in ln K against 1/T (van 't Hoff).
const KP = [[300,4.34e-3],[400,1.64e-4],[450,4.51e-5],[500,1.45e-5],[550,5.38e-6],[600,2.25e-6]];
function Kp(tc){
  const inv = 1/(tc+273.15);
  let i = 0; while (i < KP.length-2 && tc > KP[i+1][0]) i++;
  const [a,ka] = KP[i], [b,kb] = KP[i+1], ia = 1/(a+273.15), ib = 1/(b+273.15), f = (inv-ia)/(ib-ia);
  return Math.exp(Math.log(ka) + f*(Math.log(kb) - Math.log(ka)));
}
// Ideal gas: each molecule adds PC*(T/673.15)/V atm. PC is set so the starting mix settles at 200 atm at 400 °C with the piston at 1.
// Equilibrium NH3 mole fraction at 200 atm, 400 °C for a 1:3 feed: x^2/(1-x)^4 = Kp P^2 27/256.
function feedFraction(K, P){ const c = K*P*P*27/256; let lo = 0, hi = 0.999; for (let k=0;k<60;k++){ const x=(lo+hi)/2; (x*x/Math.pow(1-x,4) < c) ? lo = x : hi = x; } return (lo+hi)/2; }
const N0 = 120, H0 = 360;                                  // starting molecules: 120 N2 + 360 H2
const PC = 200 / ((N0+H0) / (1 + feedFraction(Kp(400), 200)));
const kPer = (tc, V) => PC*((tc+273.15)/673.15)/V;           // atm per molecule
// equilibrium amount of NH3 for a given atom inventory, volume and temperature
function equilibrium(NN, NH, V, tc){
  const K = Kp(tc), k = kPer(tc, V), amax = Math.min(NN, NH/3);
  let lo = 0, hi = amax;
  for (let it=0; it<60; it++){ const a = (lo+hi)/2, n2 = (NN-a)/2, h2 = (NH-3*a)/2; (a*a < K*k*k*n2*h2*h2*h2) ? lo = a : hi = a; }
  const a = (lo+hi)/2, tot = (NN-a)/2 + (NH-3*a)/2 + a;
  return {nh3:a, frac:a/tot, P:tot*k};
}

// ---------- state ----------
const S = { tc:400, V:1, Vt:1, cat:true, speed:1, playing:true, step:0, t:0, fe:0, re:0, feAcc:0, reAcc:0,
            show:{labels:true, flash:true, orbit:false}, P:0, pct:0, target:0, Q:0, K:Kp(400) };
const BOX = 10, HREF = 20;                                  // half-width and height (piston at 1) in scene units
let seed = 7; const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const mols = [];   // {k:'N2'|'H2'|'NH3', p:[x,y,z], v:[..], u:[θ,φ], w, born}
const SPEED = {N2:5.5, H2:9.5, NH3:7};
function newMol(k, p, born = -9){
  const th = rnd()*Math.PI*2, ph = Math.acos(2*rnd()-1), s = SPEED[k]*Math.sqrt((S.tc+273.15)/673.15);
  return {k, p:p.slice(), v:[s*Math.sin(ph)*Math.cos(th), s*Math.cos(ph), s*Math.sin(ph)*Math.sin(th)], u:[rnd()*6.3, rnd()*3.1], w:(rnd()-0.5)*3, born};
}
const H = () => HREF*S.V;
function randPos(){ return [(rnd()*2-1)*(BOX-1.5), 1.5 + rnd()*(H()-3), (rnd()*2-1)*(BOX-1.5)]; }
function refill(){ mols.length = 0; for (let i=0;i<N0;i++) mols.push(newMol('N2', randPos())); for (let i=0;i<H0;i++) mols.push(newMol('H2', randPos())); hist.length = 0; marks.length = 0; S.t = 0; }
const count = () => { const c = {N2:0, H2:0, NH3:0}; for (const m of mols) c[m.k]++; return c; };

// ---------- reactions (stochastic mass action; ratio of the two rates fixed by Kp) ----------
// forward rate = kr*Kp*k^2*nN2*nH2^3, reverse rate = kr*nNH3^2  -> equal exactly when Q = Kp.
const EA_R = 7000;     // illustrative activation temperature (K): rates roughly triple per +50 °C
function rates(c){
  const k = kPer(S.tc, S.V), K = Kp(S.tc);
  const kr = 10/(124*124) * Math.exp(EA_R*(1/673.15 - 1/(S.tc+273.15))) * (S.cat ? 1 : 0.06);
  return {f: kr*K*k*k*c.N2*Math.pow(c.H2,3), r: kr*c.NH3*c.NH3};
}
function poisson(l){ if (l <= 0) return 0; if (l > 30) return Math.max(0, Math.round(l + Math.sqrt(l)*(rnd()+rnd()+rnd()-1.5)*2)); let L = Math.exp(-l), k = 0, p = 1; do { k++; p *= rnd(); } while (p > L); return k-1; }
const d2 = (a, b) => (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2;
function removeAt(i){ mols[i] = mols[mols.length-1]; mols.pop(); }
function nearest(kind, p, n, skip){
  const out = [];
  mols.forEach((m, i) => { if (m.k !== kind || i === skip) return; const d = d2(m.p, p); if (out.length < n){ out.push([d,i]); out.sort((a,b)=>a[0]-b[0]); } else if (d < out[n-1][0]){ out[n-1] = [d,i]; out.sort((a,b)=>a[0]-b[0]); } });
  return out.map(o => o[1]);
}
function forward(){
  const ns = mols.map((m,i) => m.k === 'N2' ? i : -1).filter(i => i >= 0); if (!ns.length) return false;
  const i = ns[Math.floor(rnd()*ns.length)], p = mols[i].p.slice(), hs = nearest('H2', p, 3); if (hs.length < 3) return false;
  [i, ...hs].sort((a,b) => b-a).forEach(removeAt);
  mols.push(newMol('NH3', [p[0]-0.9, p[1], p[2]], S.t), newMol('NH3', [p[0]+0.9, p[1], p[2]], S.t)); flash(p, true); return true;
}
function reverse(){
  const ns = mols.map((m,i) => m.k === 'NH3' ? i : -1).filter(i => i >= 0); if (ns.length < 2) return false;
  const i = ns[Math.floor(rnd()*ns.length)], j = nearest('NH3', mols[i].p, 1, i)[0];
  const p = mols[i].p.map((x, a) => (x + mols[j].p[a])/2); [i, j].sort((a,b) => b-a).forEach(removeAt);
  mols.push(newMol('N2', p, S.t)); for (let k=0;k<3;k++) mols.push(newMol('H2', [p[0]+(rnd()-0.5)*2, p[1]+(rnd()-0.5)*2, p[2]+(rnd()-0.5)*2], S.t)); flash(p, false); return true;
}

// ---------- the guided steps ----------
const STEPS = [
  {name:'Both ways at once', nick:'dynamic equilibrium', act(){ refill(); mark('refill'); },
   text:'Nitrogen and hydrogen join to make ammonia, and ammonia splits back apart, at the same time. When the two rates match, the amounts stop changing, even though molecules never stop reacting.'},
  {name:'Squeeze it', nick:'pressure up', act(){ setVol(0.55); },
   text:'Push the piston down and the pressure jumps. The reaction answers by making more ammonia: 4 gas molecules become 2, and fewer molecules push less. Part of the extra pressure goes away.'},
  {name:'Heat it', nick:'temperature up', act(){ setTemp(520); },
   text:'Making ammonia gives out heat (ΔH = −92.4 kJ/mol). Add heat and the reaction runs backwards to soak it up, so there is less ammonia. K itself falls: 1.64×10⁻⁴ at 400 °C, 1.45×10⁻⁵ at 500 °C.'},
  {name:'Add nitrogen', nick:'more reactant', act(){ addN2(); },
   text:'Add more N₂ and the reaction uses some of it up, making more ammonia, until Q equals K again.'},
  {name:'Take ammonia out', nick:'less product', act(){ removeNH3(); },
   text:'Real plants cool the gas so ammonia turns liquid and drains away. The reaction makes more to replace it, so almost all the nitrogen ends up as ammonia over many passes.'},
  {name:'Catalyst', nick:'faster, not further', act(){ setCat(!S.cat); },
   text:'Iron speeds up both directions by the same factor. Equilibrium arrives sooner, but where it ends up does not change. Turn it off and watch the curve crawl.'}
];
function goStep(k, apply = true){ S.step = (k + STEPS.length) % STEPS.length; const s = STEPS[S.step];
  $('sNum').textContent = S.step + 1; $('sName').textContent = s.name; $('sNick').textContent = '“' + s.nick + '”'; $('sText').textContent = s.text;
  $('slist').querySelectorAll('button').forEach(b => b.setAttribute('aria-current', String(+b.dataset.k === S.step)));
  if (apply) s.act(); }
STEPS.forEach((s, k) => { const b = document.createElement('button'); b.dataset.k = k; b.innerHTML = `<span class="sw" style="background:${['#fff','#c8371f','#d2402a','#2f6fb5','#c48a1c','#8a8d90'][k]}"></span><span>${k+1}. ${s.name}</span><span class="deg">${s.nick}</span>`; b.onclick = () => goStep(k); $('slist').append(b); });

// ---------- actions ----------
const marks = [];
function mark(label){ marks.push({t:S.t, label}); }
function setVol(v){ S.Vt = v; $('vol').value = v; mark(v < S.V ? 'squeeze' : 'release'); }
function setTemp(t){ S.tc = t; $('temp').value = t; $('tLab').textContent = t + ' °C'; mark(t + ' °C'); }
function addN2(){ for (let i=0;i<40;i++) mols.push(newMol('N2', [(rnd()*2-1)*(BOX-1.5), H()-1.5, (rnd()*2-1)*(BOX-1.5)], S.t)); mark('+N₂'); }
function removeNH3(){ for (let i=mols.length-1;i>=0;i--) if (mols[i].k === 'NH3') removeAt(i); mark('−NH₃'); }
function setCat(on){ S.cat = on; $('bCat').textContent = on ? 'Iron catalyst on' : 'Catalyst off'; $('bCat').setAttribute('aria-pressed', String(on)); mark(on ? 'catalyst on' : 'catalyst off'); }
$('vol').oninput = e => { S.Vt = +e.target.value; };
$('vol').onchange = () => { mark(S.Vt < S.V ? 'squeeze' : 'release'); goStep(1, false); };
$('temp').oninput = e => { S.tc = +e.target.value; $('tLab').textContent = S.tc + ' °C'; };
$('temp').onchange = () => { mark(S.tc + ' °C'); goStep(2, false); };
$('bAdd').onclick = () => { addN2(); goStep(3, false); }; $('bRem').onclick = () => { removeNH3(); goStep(4, false); }; $('bCat').onclick = () => { setCat(!S.cat); goStep(5, false); };
$('bReset').onclick = () => goStep(0);
$('bNext').onclick = () => goStep(S.step + 1); $('bBack').onclick = () => goStep(S.step - 1);
function syncPlay(){ $('bPlay').textContent = S.playing ? 'Pause' : 'Play'; $('bPlay').setAttribute('aria-pressed', String(S.playing)); }
$('bPlay').onclick = () => { S.playing = !S.playing; syncPlay(); };
document.querySelectorAll('[data-speed]').forEach(b => b.onclick = () => { S.speed = +b.dataset.speed; document.querySelectorAll('[data-speed]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
[['tgLabels','labels'],['tgFlash','flash'],['tgOrbit','orbit']].forEach(([id,k]) => $(id).onclick = () => { S.show[k] = !S.show[k]; $(id).setAttribute('aria-pressed', String(S.show[k])); });

// ---------- 3D scene ----------
const canvas = $('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true, preserveDrawingBuffer: RECORD});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 900);
const target = new THREE.Vector3(0, 12, 0);
const orbit = { az: -0.6, el: 0.32, dist: 92 };
function placeCam(){ const fit = Math.max(1, 1.1/Math.max(0.3, camera.aspect)); const d = orbit.dist*fit, c = Math.cos(orbit.el);
  camera.position.set(target.x + d*c*Math.sin(orbit.az), target.y + d*Math.sin(orbit.el), target.z + d*c*Math.cos(orbit.az)); camera.lookAt(target); }
scene.add(new THREE.AmbientLight(0xffffff, 0.62));
const sun = new THREE.DirectionalLight(0xffffff, 0.7); sun.position.set(-40, 70, 50); scene.add(sun);
const grad = new THREE.DataTexture(new Uint8Array([150,150,150,255, 205,205,205,255, 255,255,255,255]), 3, 1, THREE.RGBAFormat);
grad.minFilter = grad.magFilter = THREE.NearestFilter; grad.needsUpdate = true;
const INK = new THREE.LineBasicMaterial({color:0x1c1d1f});
const toon = c => new THREE.MeshToonMaterial({color:c, gradientMap:grad});
// reactor: dashed glass walls, base plate with heater, piston
const walls = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(BOX*2, 1, BOX*2)), new THREE.LineDashedMaterial({color:0x55585c, dashSize:0.9, gapSize:0.6}));
scene.add(walls);
const glass = new THREE.Mesh(new THREE.BoxGeometry(BOX*2, 1, BOX*2), new THREE.MeshBasicMaterial({color:0x9fc3d8, transparent:true, opacity:0.07, depthWrite:false, side:THREE.DoubleSide}));
scene.add(glass);
const baseGeo = new THREE.BoxGeometry(BOX*2+3, 2, BOX*2+3), baseMat = toon(0x6d6f72);
const base = new THREE.Mesh(baseGeo, baseMat); base.position.y = -1; base.add(new THREE.LineSegments(new THREE.EdgesGeometry(baseGeo), INK)); scene.add(base);
const coilMat = new THREE.MeshBasicMaterial({color:0x553322});
for (let k=-3; k<=3; k++){ const g = new THREE.BoxGeometry(BOX*2-2, 0.35, 0.6); const m = new THREE.Mesh(g, coilMat); m.position.set(0, 0.2, k*2.6); scene.add(m); }
const piston = new THREE.Group(); scene.add(piston);
const plateGeo = new THREE.BoxGeometry(BOX*2-0.2, 1.4, BOX*2-0.2); const plate = new THREE.Mesh(plateGeo, toon(0xc9ccc8)); plate.add(new THREE.LineSegments(new THREE.EdgesGeometry(plateGeo), INK)); piston.add(plate);
const rodGeo = new THREE.CylinderGeometry(1.1, 1.1, 18, 16); const rod = new THREE.Mesh(rodGeo, toon(0x8a8d90)); rod.position.y = 9.7; rod.add(new THREE.LineSegments(new THREE.EdgesGeometry(rodGeo, 30), INK)); piston.add(rod);
const ground = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(60, 60).rotateX(-Math.PI/2)), new THREE.LineBasicMaterial({color:0xc9cdca})); ground.position.y = -2; scene.add(ground);
// atoms: instanced spheres with an inked outline shell
const MAXA = 2400;
function atoms(r, color){
  const g = new THREE.SphereGeometry(r, 14, 10), m = new THREE.InstancedMesh(g, toon(color), MAXA);
  const o = new THREE.InstancedMesh(new THREE.SphereGeometry(r*1.14, 12, 8), new THREE.MeshBasicMaterial({color:0x1c1d1f, side:THREE.BackSide}), MAXA);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); o.instanceMatrix.setUsage(THREE.DynamicDrawUsage); scene.add(m, o); return {m, o, n:0};
}
const AN = atoms(0.62, 0x2f6fb5), AH = atoms(0.42, 0xf4f4ef), AG = atoms(0.95, 0xffb347);   // AG: glow on freshly made NH3
AG.m.material = new THREE.MeshBasicMaterial({color:0xffb347, transparent:true, opacity:0.35, depthWrite:false}); AG.o.visible = false;
const M4 = new THREE.Matrix4(), V3 = new THREE.Vector3(), Q4 = new THREE.Quaternion(), SC = new THREE.Vector3(1,1,1);
function put(A, x, y, z, s = 1){ M4.compose(V3.set(x,y,z), Q4, SC.set(s,s,s)); A.m.setMatrixAt(A.n, M4); A.o.setMatrixAt(A.n, M4); A.n++; }
// reaction flashes: rings that face the camera
const flashes = [];
const ringGeo = new THREE.RingGeometry(1.2, 1.7, 28);
for (let i=0;i<40;i++){ const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({color:0xe8892c, transparent:true, opacity:0, depthWrite:false, side:THREE.DoubleSide})); m.visible = false; scene.add(m); flashes.push({m, t:-9}); }
let fi = 0;
function flash(p, fwd){ if (fwd) S.feAcc++; else S.reAcc++; const f = flashes[fi++ % flashes.length]; f.t = S.t; f.m.position.set(p[0], p[1], p[2]); f.m.material.color.set(fwd ? 0xe8892c : 0x2f6fb5); }

// balloons that follow one molecule of each kind
const balEls = {}, leaderEls = [];
const svg = $('leaders');
const LABS = [['1','Nitrogen N₂','N2'], ['2','Hydrogen H₂','H2'], ['3','Ammonia NH₃','NH3'], ['4','Piston','piston'], ['5','Heater','heater']];
LABS.forEach(([n,name], idx) => { const d = document.createElement('div'); d.className = 'bal'; const b = document.createElement('b'); b.textContent = n; const s = document.createElement('span'); s.textContent = name; d.append(b, s); (idx < 3 ? $('balL') : $('balR')).append(d); balEls[n] = d;
  const l = document.createElementNS('http://www.w3.org/2000/svg','path'); l.setAttribute('fill','none'); l.setAttribute('stroke','#1c1d1f'); l.setAttribute('stroke-width','1');
  const dot = document.createElementNS('http://www.w3.org/2000/svg','circle'); dot.setAttribute('r','3'); dot.setAttribute('fill','#1c1d1f'); svg.append(l, dot); leaderEls.push({l, dot}); });
const tracked = {};
function trackedPos(kind){
  let m = tracked[kind]; if (!m || !mols.includes(m)){ m = tracked[kind] = mols.find(x => x.k === kind && Math.abs(x.p[0]) < 6 && Math.abs(x.p[2]) < 6) || mols.find(x => x.k === kind); }
  return m ? new THREE.Vector3(...m.p) : null;
}
function updateLeaders(){
  const wrap = $('viewWrap').getBoundingClientRect();
  LABS.forEach(([n,,kind], idx) => {
    const p = kind === 'piston' ? new THREE.Vector3(BOX*0.7, H()+0.7, BOX*0.7) : kind === 'heater' ? new THREE.Vector3(BOX*0.6, 0.3, BOX*0.8) : trackedPos(kind);
    const on = S.show.labels && p; balEls[n].style.visibility = on ? 'visible' : 'hidden';
    const {l, dot} = leaderEls[idx]; l.style.display = dot.style.display = on ? '' : 'none'; if (!on) return;
    const v = p.project(camera); const px = (v.x*0.5+0.5)*wrap.width, py = (-v.y*0.5+0.5)*wrap.height;
    const b = balEls[n].querySelector('b').getBoundingClientRect(); const left = idx < 3;
    const bx = (left ? b.right : b.left) - wrap.left, by = b.top + b.height/2 - wrap.top, kx = bx + (left ? 18 : -18);
    l.setAttribute('d', `M${bx},${by} L${kx},${by} L${px},${py}`); dot.setAttribute('cx', px); dot.setAttribute('cy', py);
  });
}

// orbit by drag, zoom by wheel/pinch
let drag = null; const pinch = new Map();
canvas.addEventListener('pointerdown', e => { e.preventDefault(); canvas.setPointerCapture(e.pointerId); pinch.set(e.pointerId, [e.clientX, e.clientY]); drag = {x:e.clientX, y:e.clientY, az:orbit.az, el:orbit.el}; });
canvas.addEventListener('pointermove', e => {
  if (!pinch.has(e.pointerId)) return; const prev = pinch.get(e.pointerId); pinch.set(e.pointerId, [e.clientX, e.clientY]);
  if (pinch.size === 2){ const [a,b] = [...pinch.values()]; const d = Math.hypot(a[0]-b[0], a[1]-b[1]); const o = [...pinch.keys()].find(k => k !== e.pointerId); const q = pinch.get(o); const d0 = Math.hypot(prev[0]-q[0], prev[1]-q[1]); orbit.dist = Math.min(200, Math.max(45, orbit.dist*d0/d)); return; }
  if (drag){ orbit.az = drag.az - (e.clientX - drag.x)*0.008; orbit.el = Math.min(1.4, Math.max(-0.1, drag.el + (e.clientY - drag.y)*0.006)); }
});
['pointerup','pointercancel'].forEach(t => canvas.addEventListener(t, e => { pinch.delete(e.pointerId); if (!pinch.size) drag = null; }));
canvas.addEventListener('wheel', e => { e.preventDefault(); orbit.dist = Math.min(200, Math.max(45, orbit.dist*(1 + e.deltaY*0.001))); }, {passive:false});

// ---------- 2D canvases ----------
function setupCanvas(c){ const r = c.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio||1, 2); c.width = Math.max(10, r.width*dpr); c.height = Math.max(10, r.height*dpr); const ctx = c.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); return {ctx, w:r.width, h:r.height}; }
let TC, QC, CC;
function sizeAll(){ const r = $('viewWrap').getBoundingClientRect(); renderer.setSize(r.width, r.height, false); camera.aspect = r.width/Math.max(1, r.height); camera.updateProjectionMatrix(); svg.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`); TC = setupCanvas($('tach')); QC = setupCanvas($('qk')); CC = setupCanvas($('chart')); }
function drawGauge(){
  const {ctx,w,h} = TC; ctx.clearRect(0,0,w,h); const cx = w/2, cy = h*0.86, rad = Math.min(w*0.44, h*0.8);
  const a0 = Math.PI*1.08, a1 = Math.PI*1.92, MAXP = 500, A = v => a0 + (a1-a0)*Math.min(v, MAXP)/MAXP;
  ctx.lineWidth = 2; ctx.strokeStyle = '#1c1d1f'; ctx.beginPath(); ctx.arc(cx,cy,rad,a0,a1); ctx.stroke();
  ctx.strokeStyle = '#2f6fb5'; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(cx,cy,rad-4,A(150),A(250)); ctx.stroke();
  ctx.fillStyle = '#1c1d1f'; ctx.font = '11px "Geist Mono", monospace'; ctx.textAlign = 'center';
  for (let k=0;k<=500;k+=100){ const a = A(k); ctx.lineWidth = 1.5; ctx.strokeStyle = '#1c1d1f'; ctx.beginPath(); ctx.moveTo(cx+Math.cos(a)*(rad-10), cy+Math.sin(a)*(rad-10)); ctx.lineTo(cx+Math.cos(a)*rad, cy+Math.sin(a)*rad); ctx.stroke(); ctx.fillText(k, cx+Math.cos(a)*(rad-24), cy+Math.sin(a)*(rad-24)+4); }
  const a = A(S.P); ctx.strokeStyle = '#c8371f'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx+Math.cos(a)*(rad-14), cy+Math.sin(a)*(rad-14)); ctx.stroke();
  ctx.fillStyle = '#1c1d1f'; ctx.beginPath(); ctx.arc(cx,cy,4,0,7); ctx.fill();
  const fs = Math.round(Math.max(15, Math.min(28, rad*0.22))); ctx.font = '400 '+fs+'px "Instrument Serif", serif'; ctx.fillText(Math.round(S.P) + ' atm', cx, cy-rad*0.14);
  ctx.font = '10px "Geist Mono", monospace'; ctx.fillStyle = '#55585c'; ctx.fillText('blue band = industrial 150–250', cx, cy-rad*0.14+13);
}
function drawQK(){
  const {ctx,w,h} = QC; ctx.clearRect(0,0,w,h); const L = -7, R = -1, X = v => 14 + (Math.log10(Math.max(1e-12, v)) - L)/(R-L)*(w-28), y = h*0.42;
  ctx.strokeStyle = '#1c1d1f'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(14, y); ctx.lineTo(w-14, y); ctx.stroke();
  ctx.font = '10px "Geist Mono", monospace'; ctx.fillStyle = '#55585c'; ctx.textAlign = 'center';
  for (let e=L; e<=R; e++){ const x = X(Math.pow(10, e)); ctx.beginPath(); ctx.moveTo(x, y-4); ctx.lineTo(x, y+4); ctx.stroke(); ctx.fillText('10' + String(e).replace('-', '⁻').replace(/\d/g, d => '⁰¹²³⁴⁵⁶⁷⁸⁹'[d]), x, y+16); }
  const xk = X(S.K), xq = X(S.Q);
  ctx.strokeStyle = '#2f6fb5'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(xk, y-14); ctx.lineTo(xk, y+8); ctx.stroke(); ctx.fillStyle = '#2f6fb5'; ctx.fillText('K', xk, y-18);
  ctx.fillStyle = '#c8371f'; ctx.beginPath(); ctx.arc(xq, y, 6, 0, 7); ctx.fill(); ctx.fillText('Q', xq, y-12 + (Math.abs(xq-xk) < 14 ? -10 : 0));
  const r = S.Q/S.K; ctx.font = '12px "Geist Mono", monospace'; ctx.fillStyle = '#1c1d1f'; ctx.textAlign = 'left';
  ctx.fillText(r < 0.8 ? 'Q < K  →  makes more NH₃' : r > 1.25 ? 'Q > K  ←  splits NH₃' : 'Q ≈ K  ⇌  at equilibrium', 14, h-8);
}
const hist = []; const CH = {l:42, r:44, t:22, b:22}, WIN = 40;
function drawChart(){
  const {ctx,w,h} = CC; ctx.clearRect(0,0,w,h); const t1 = Math.max(WIN, S.t), t0 = t1 - WIN;
  const X = t => CH.l + (t-t0)/WIN*(w-CH.l-CH.r), Y = p => h-CH.b - p/80*(h-CH.t-CH.b), YP = p => h-CH.b - p/500*(h-CH.t-CH.b);
  ctx.strokeStyle = '#e1e5e3'; ctx.lineWidth = 1; ctx.font = '10px "Geist Mono", monospace'; ctx.fillStyle = '#55585c';
  for (let p=0;p<=80;p+=20){ ctx.beginPath(); ctx.moveTo(CH.l, Y(p)); ctx.lineTo(w-CH.r, Y(p)); ctx.stroke(); ctx.textAlign = 'right'; ctx.fillText(p + '%', CH.l-5, Y(p)+3); }
  ctx.textAlign = 'left'; for (let p=0;p<=500;p+=250) ctx.fillText(p + ' atm', w-CH.r+4, YP(p)+3);
  marks.forEach(m => { if (m.t < t0) return; const x = X(m.t); ctx.strokeStyle = '#8a8d90'; ctx.setLineDash([3,3]); ctx.beginPath(); ctx.moveTo(x, CH.t-6); ctx.lineTo(x, h-CH.b); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#1c1d1f'; ctx.textAlign = 'left'; ctx.fillText(m.label, x+3, CH.t-8+10); });
  const line = (key, Yf, col, lw, dash) => { ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.setLineDash(dash); ctx.beginPath(); let st = false; hist.forEach(s => { if (s.t < t0) return; st ? ctx.lineTo(X(s.t), Yf(s[key])) : ctx.moveTo(X(s.t), Yf(s[key])); st = true; }); ctx.stroke(); ctx.setLineDash([]); };
  line('P', YP, '#b9bdbb', 1.2, []); line('target', Y, '#2f6fb5', 1.6, [6,4]); line('pct', Y, '#c8371f', 2.2, []);
  ctx.fillStyle = '#55585c'; ctx.textAlign = 'right'; ctx.fillText('model time →', w-CH.r, h-6);
}

// ---------- update / draw ----------
let sampleAcc = 0;
function update(dt){
  const sdt = S.playing ? dt*S.speed : 0;
  // piston glides toward its target; molecules above it get pushed down
  S.V += (S.Vt - S.V)*Math.min(1, dt*3);
  if (sdt > 0){
    S.t += sdt;
    const steps = Math.max(1, Math.ceil(sdt/0.02));
    for (let s=0; s<steps; s++){
      const h = sdt/steps, c = count(), r = rates(c);
      let nf = poisson(r.f*h), nr = poisson(r.r*h);
      while (nf-- > 0) if (!forward()) break;
      while (nr-- > 0) if (!reverse()) break;
    }
    const top = H(), vs = Math.sqrt((S.tc+273.15)/673.15);
    for (const m of mols){
      const sp = Math.hypot(...m.v), want = SPEED[m.k]*vs; if (sp > 0) for (let a=0;a<3;a++) m.v[a] *= 1 + (want/sp - 1)*Math.min(1, sdt*2);   // thermalise to the set temperature
      for (let a=0;a<3;a++) m.p[a] += m.v[a]*sdt;
      const lim = BOX - 1.2;
      for (const a of [0, 2]){ if (m.p[a] > lim){ m.p[a] = lim; m.v[a] = -Math.abs(m.v[a]); } if (m.p[a] < -lim){ m.p[a] = -lim; m.v[a] = Math.abs(m.v[a]); } }
      if (m.p[1] < 1.2){ m.p[1] = 1.2; m.v[1] = Math.abs(m.v[1]); }
      if (m.p[1] > top - 1.6){ m.p[1] = top - 1.6; m.v[1] = -Math.abs(m.v[1]); }
      m.u[0] += m.w*sdt;
    }
  }
  const c = count(), k = kPer(S.tc, S.V), tot = c.N2 + c.H2 + c.NH3;
  S.P = tot*k; S.pct = tot ? c.NH3/tot*100 : 0; S.K = Kp(S.tc);
  S.Q = (c.N2 && c.H2) ? (c.NH3*c.NH3)/(c.N2*Math.pow(c.H2,3))/(k*k) : 1;
  const eq = equilibrium(2*c.N2 + c.NH3, 2*c.H2 + 3*c.NH3, S.V, S.tc); S.target = eq.frac*100;
  sampleAcc += sdt; if (sampleAcc >= 0.1 || !hist.length){ sampleAcc = 0; hist.push({t:S.t, pct:S.pct, target:S.target, P:S.P}); if (hist.length > 2000) hist.splice(0, 500); }
  S.fe = S.feAcc; S.re = S.reAcc; S.feAcc = S.reAcc = 0;
  if (S.show.orbit) orbit.az += dt*0.25;
  // panels
  $('sNow').textContent = `Now ${S.pct.toFixed(0)}% ammonia, heading for ${S.target.toFixed(0)}%`;
  $('sCount').textContent = `N₂ ${c.N2} · H₂ ${c.H2} · NH₃ ${c.NH3} · ${S.tc} °C · Kp ${S.K.toExponential(2)}`;
}
const tmpC = new THREE.Color();
function draw(){
  placeCam();
  const top = H();
  walls.scale.y = glass.scale.y = top; walls.position.y = glass.position.y = top/2; walls.computeLineDistances();
  piston.position.y = top + 0.7;
  const heat = (S.tc - 300)/300; coilMat.color.copy(tmpC.set(0x553322)).lerp(new THREE.Color(0xff6a1a), Math.max(0, Math.min(1, heat*1.1)));
  AN.n = AH.n = AG.n = 0;
  const e1 = new THREE.Vector3(), e2 = new THREE.Vector3(), u = new THREE.Vector3();
  for (const m of mols){
    const [x, y, z] = m.p, th = m.u[0], ph = m.u[1];
    u.set(Math.sin(ph)*Math.cos(th), Math.cos(ph), Math.sin(ph)*Math.sin(th));
    e1.set(-u.z, 0, u.x); if (e1.lengthSq() < 1e-4) e1.set(1, 0, 0); e1.normalize(); e2.crossVectors(u, e1);
    if (m.k === 'N2'){ put(AN, x+u.x*0.55, y+u.y*0.55, z+u.z*0.55); put(AN, x-u.x*0.55, y-u.y*0.55, z-u.z*0.55); }
    else if (m.k === 'H2'){ put(AH, x+u.x*0.36, y+u.y*0.36, z+u.z*0.36); put(AH, x-u.x*0.36, y-u.y*0.36, z-u.z*0.36); }
    else {
      put(AN, x, y, z);
      for (let k=0;k<3;k++){ const a = k*2.094; const hx = (e1.x*Math.cos(a) + e2.x*Math.sin(a))*0.78 - u.x*0.3, hy = (e1.y*Math.cos(a) + e2.y*Math.sin(a))*0.78 - u.y*0.3, hz = (e1.z*Math.cos(a) + e2.z*Math.sin(a))*0.78 - u.z*0.3; put(AH, x+hx, y+hy, z+hz); }
      const age = S.t - m.born; if (age < 1.2) put(AG, x, y, z, 1 + age*0.6);
    }
  }
  for (const A of [AN, AH, AG]){ A.m.count = A.o.count = A.n; A.m.instanceMatrix.needsUpdate = A.o.instanceMatrix.needsUpdate = true; }
  for (const f of flashes){ const age = S.t - f.t; const on = S.show.flash && age >= 0 && age < 0.7; f.m.visible = on; if (on){ f.m.quaternion.copy(camera.quaternion); f.m.scale.setScalar(0.6 + age*2.2); f.m.material.opacity = 0.9*(1 - age/0.7); } }
  renderer.render(scene, camera); updateLeaders(); drawGauge(); drawQK(); drawChart();
}

refill(); goStep(0, false); sizeAll(); window.addEventListener('resize', sizeAll);
if (document.fonts) document.fonts.ready.then(sizeAll);
let last = performance.now();
function frame(now){ const dt = Math.max(0, Math.min(0.05, (now-last)/1000)); last = now; update(dt); draw(); requestAnimationFrame(frame); }
if (RECORD){ window.__engine = { advance(dt){ update(dt); draw(); }, state: S, resize: sizeAll }; update(0); draw(); }
else requestAnimationFrame(frame);
})();
