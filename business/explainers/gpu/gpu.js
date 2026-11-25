(function(){
'use strict';
const $ = id => document.getElementById(id);
const SHORT = location.hash === '#short';
const RECORD = location.hash === '#record' || SHORT;
if (SHORT) document.body.classList.add('short');

// ---------- pipeline model ----------
const CYC = 64;
const STAGES = [
  {name:'Fetch & decode', nick:'fetch', col:'#2f6fb5',
   text:'The warp scheduler picks a ready warp (32 threads that run in lock-step), fetches its next instruction from the instruction cache and decodes it.'},
  {name:'Issue', nick:'issue', col:'#c48a1c',
   text:'The instruction is issued to an execution unit once its operands are ready in the register file. If this warp must wait, the scheduler switches to another warp, which hides the waiting time.'},
  {name:'Execute', nick:'execute', col:'#c48a1c',
   text:'CUDA cores do ordinary maths (FP32 and INT32). Tensor cores multiply small matrices for AI. RT cores test rays against triangles for ray tracing.'},
  {name:'Writeback', nick:'write', col:'#8a8d90',
   text:'Results go back to the register file. Loads and stores pass through L1 / shared memory, then L2 and the memory controllers out to HBM. Two threads hitting the same shared-memory bank must take turns: a bank conflict.'}
];
const STALL = {name:'Stall', nick:'waiting for a ready warp', col:'#b9bdbb', text:'No warp is ready this cycle. With more work on the GPU, more warps are resident and the scheduler can usually find one to run.'};
const KIND = { alu:'FP32 / INT32 maths', tensor:'Tensor-core matrix multiply', rt:'RT-core ray–triangle test', mem:'Load / store to memory' };
const PROFILE = [ {alu:.45, tensor:.05, rt:.30, mem:.20, name:'graphics'}, {alu:.25, tensor:.55, rt:0, mem:.20, name:'AI'},
                  {alu:.70, tensor:.05, rt:.05, mem:.20, name:'shader'}, {alu:.30, tensor:.05, rt:0, mem:.65, name:'memory-bound'} ];
function rng(seed){ return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function makeSchedule(sm, load){
  const r = rng(1000 + sm*97 + Math.round(load*10)), P = PROFILE[sm % 4];
  const segs = []; let c = 0, hits = 0, mems = 0;
  while (c < CYC){
    if (r() > 0.25 + 0.75*load){ const n = 1 + Math.floor(r()*4); segs.push({s:-1, a:c, b:c+n}); c += n; continue; }  // stall bubble
    const x = r(); let kind = 'alu', acc = 0; for (const k of ['alu','tensor','rt','mem']){ acc += P[k]; if (x < acc){ kind = k; break; } }
    const push = (s, n, extra) => { segs.push(Object.assign({s, a:c, b:c+n, kind}, extra||{})); c += n; };
    push(0, 2); push(1, 1);
    push(2, kind === 'tensor' ? 5 : kind === 'rt' ? 6 : 3);
    if (kind === 'mem'){
      mems++; const hit = r() < 0.92 - 0.35*load*P.mem; if (hit) hits++;
      const conflict = r() < 0.18 + 0.2*load;
      push(3, (hit ? 3 : 8) + (conflict ? 2 : 0), {hit, conflict});
    } else push(3, 1);
  }
  segs.forEach(g => { g.b = Math.min(g.b, CYC); });
  return {segs: segs.filter(g => g.a < CYC), hit: mems ? hits/mems : 1, memShare: P.mem};
}
const NSM = 12;
let sched = [];
function rebuild(load){ sched = []; for (let i=0;i<NSM;i++) sched.push(makeSchedule(i, load)); }
const segAt = (sm, cyc) => { const t = ((cyc % CYC) + CYC) % CYC; return sched[sm].segs.find(g => t >= g.a && t < g.b) || {s:-1, a:0, b:1}; };

// ---------- state ----------
const S = { cyc: 3, util: 0.25, target: 0.25, load: 0.25, clock: 1800, power: 120, speed: 0.0833333, playing: true, follow: 0,
            hbm: 0.1, show:{pkg:true, flow:true, labels:true, orbit:false} };
rebuild(0.25); let builtLoad = 0.25;
const BASE_RATE = 120;   // cycles per second shown at 1×; real clock runs ~20 million times faster

// ---------- three.js ----------
const canvas = $('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true, preserveDrawingBuffer: RECORD});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 800);
const target = new THREE.Vector3(0, -1, 3);
const orbit = { az: -0.42, el: 0.86, dist: 150 };
function placeCam(){ const fit = Math.max(1, 1.3/Math.max(0.3, camera.aspect)); const d = orbit.dist*fit, c = Math.cos(orbit.el);
  camera.position.set(target.x + d*c*Math.sin(orbit.az), target.y + d*Math.sin(orbit.el), target.z + d*c*Math.cos(orbit.az)); camera.lookAt(target); }
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.75); sun.position.set(-30, 70, 40); scene.add(sun);
const grad = new THREE.DataTexture(new Uint8Array([150,150,150,255, 205,205,205,255, 255,255,255,255]), 3, 1, THREE.RGBAFormat);
grad.minFilter = grad.magFilter = THREE.NearestFilter; grad.needsUpdate = true;
const toon = c => new THREE.MeshToonMaterial({color:c, gradientMap:grad});
const INK = new THREE.LineBasicMaterial({color:0x1c1d1f});
const INK2 = new THREE.LineBasicMaterial({color:0x55585c, transparent:true, opacity:0.6});
function inked(geo, mat, ink=INK){ const m = new THREE.Mesh(geo, mat); m.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), ink)); return m; }
const box = (w,h,d) => new THREE.BoxGeometry(w,h,d);
const M = { sub: toon(0xcfd1cc), inter: toon(0xdcdedb), die: toon(0xe4e4e0), sm: toon(0xeeeeea), l2: toon(0xd3d5d1), mc: toon(0xc4c6c2),
            sched: toon(0x9fa2a3), reg: toon(0xc8cac6), l1: toon(0xd8d4c6), vrm: toon(0xb5b7b4) };
const pkg = new THREE.Group(); scene.add(pkg);
const chip = new THREE.Group(); scene.add(chip);

// package: substrate, interposer, HBM, power delivery
pkg.add(inked(box(74, 2, 62).translate(0, -3.6, 0), M.sub));
const balls = new THREE.InstancedMesh(new THREE.SphereGeometry(0.55, 8, 6), toon(0xb0b2ae), 23*19); let bi = 0; const mtx = new THREE.Matrix4();
for (let i=0;i<23;i++) for (let j=0;j<19;j++){ mtx.makeTranslation(-33 + i*3, -5, -27 + j*3); balls.setMatrixAt(bi++, mtx); }
pkg.add(balls);
const interposer = inked(box(56, 1, 40).translate(0, -2.1, 0), M.inter); pkg.add(interposer);
const hbmMats = [], hbm = [];
[[-23,-9],[-23,9],[23,-9],[23,9]].forEach(([x,z], k) => {
  const g = new THREE.Group(); g.position.set(x, -1.6, z);
  const mat = new THREE.MeshToonMaterial({color:0xd9dad6, gradientMap:grad, emissive:new THREE.Color(0)}); hbmMats.push(mat);
  for (let l=0;l<5;l++){ const s = inked(box(7.2, 0.7, 10), mat); s.position.y = 0.45 + l*0.85; g.add(s); }
  pkg.add(g); hbm.push(g);
});
for (let k=0;k<10;k++){ const v = inked(box(3.4, 2.6, 3.4), M.vrm); v.position.set(-30 + k*6.6, -1.3, 27); pkg.add(v);
  const cap = inked(new THREE.CylinderGeometry(0.8,0.8,1.8,14), M.reg); cap.position.set(-30 + k*6.6, -1.7, 23.3); pkg.add(cap); }
for (let k=0;k<6;k++){ const v = inked(box(2.2, 1.2, 2.2), M.vrm); v.position.set(-33 + 0, -2, -22 + k*8); pkg.add(v); }

// die
const DIE_Y = -1.0;
chip.add(inked(box(32, 1.2, 25).translate(0, DIE_Y, 0), M.die));
const TOP = DIE_Y + 0.6;
// L2 band with cells
const l2 = inked(box(26, 0.5, 4).translate(0, TOP + 0.25, 0), M.l2); chip.add(l2);
for (let k=1;k<13;k++){ const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-13 + k*2, TOP+0.51, -2), new THREE.Vector3(-13 + k*2, TOP+0.51, 2)]), INK2); chip.add(l); }
// memory controllers on the short edges
const mcs = [];
[-15, 15].forEach(x => [-8, 0, 8].forEach(z => { const m = inked(box(1.4, 0.6, 6.4).translate(x, TOP + 0.3, z), M.mc); chip.add(m); mcs.push(m); }));
// SMs
const SMX = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25];
const smPos = []; for (let r=0;r<2;r++) for (let c=0;c<6;c++) smPos.push([SMX[c], r === 0 ? 7.3 : -7.3]);
// order so that SM 0-3 are the four central SMs of the front row
const ORDER = [7,8,9,10, 6,11, 0,1,2,3,4,5];
const SMS = ORDER.map(k => smPos[k]);
const coreGeo = box(0.32, 0.32, 0.32);
const cores = new THREE.InstancedMesh(coreGeo, toon(0xffffff), NSM*4*16);
const coreBase = new THREE.Color(0xcfd0cc), coreHot = new THREE.Color(0xc48a1c), white = new THREE.Color(0xffffff);
let ci = 0; const coreIndex = [];
const smParts = [];
SMS.forEach(([sx, sz], i) => {
  const g = new THREE.Group(); g.position.set(sx, TOP, sz); chip.add(g);
  const dir = sz > 0 ? 1 : -1;            // +1 front row: L1 band faces L2 (towards z=0)
  g.add(inked(box(4.2, 0.25, 7.0).translate(0, 0.12, 0), M.sm));
  const l1 = inked(box(3.9, 0.45, 0.9).translate(0, 0.45, -dir*2.9), M.l1); g.add(l1);
  const rtMat = new THREE.MeshToonMaterial({color:0xd6d6d2, gradientMap:grad, emissive:new THREE.Color(0)});
  const rt = inked(box(1.6, 0.7, 0.8).translate(0, 0.55, dir*3.0), rtMat); g.add(rt);
  const tensors = [], scheds = [], regs = [];
  for (let q=0;q<4;q++){
    const qx = q%2 ? 1.0 : -1.0, qz = (q<2 ? -1 : 1)*1.25*dir*-1;
    const sc = inked(box(1.8, 0.35, 0.3).translate(qx, 0.4, qz - dir*0.95), M.sched); g.add(sc); scheds.push(sc);
    const rg = inked(box(0.7, 0.45, 1.3).translate(qx - 0.55, 0.45, qz), M.reg); g.add(rg); regs.push(rg);
    const tMat = new THREE.MeshToonMaterial({color:0xd0d1cd, gradientMap:grad, emissive:new THREE.Color(0)});
    const tc = inked(box(0.75, 0.75, 0.75).translate(qx + 0.5, 0.6, qz + dir*0.45), tMat); g.add(tc); tensors.push(tc);
    for (let a=0;a<4;a++) for (let b=0;b<4;b++){
      mtx.makeTranslation(sx + qx - 0.05 + a*0.36 - 0.54 + 0.55, TOP + 0.45, sz + qz - dir*0.35 + b*0.22*dir - 0.1*dir);
      cores.setMatrixAt(ci, mtx); cores.setColorAt(ci, coreBase); coreIndex.push(i); ci++;
    }
  }
  const pk = new THREE.Mesh(box(0.55, 0.55, 0.55), new THREE.MeshBasicMaterial({color:0x2f6fb5}));
  chip.add(pk);
  smParts.push({g, l1, rt, rtMat, tensors, scheds, regs, packet:pk, dir, x:sx, z:sz});
});
chip.add(cores);

// NoC curves: SM -> L2 -> memory controller -> HBM
const nocCurves = SMS.map(([sx, sz]) => {
  const side = sx < 0 ? -1 : 1, hz = sz > 0 ? 9 : -9;
  return new THREE.CatmullRomCurve3([new THREE.Vector3(sx, TOP+0.9, sz - Math.sign(sz)*2.9), new THREE.Vector3(sx, TOP+0.8, Math.sign(sz)*1.6), new THREE.Vector3(side*10, TOP+0.8, Math.sign(sz)*1.4), new THREE.Vector3(side*15, TOP+0.9, Math.sign(sz)*4), new THREE.Vector3(side*19, 0.4, hz*0.8), new THREE.Vector3(side*23, 3.0, hz)]);
});
const nocLines = new THREE.Group(); chip.add(nocLines);
nocCurves.forEach(c => { const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(c.getPoints(40)), new THREE.LineDashedMaterial({color:0x55585c, dashSize:0.6, gapSize:0.5, transparent:true, opacity:0.55})); l.computeLineDistances(); nocLines.add(l); });
const PER = window.innerWidth < 700 ? 6 : 10;
const pGeo = new THREE.BufferGeometry(), pPos = new Float32Array(NSM*PER*3), pCol = new Float32Array(NSM*PER*3);
pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3)); pGeo.setAttribute('color', new THREE.BufferAttribute(pCol, 3));
const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({size:0.75, vertexColors:true, transparent:true, opacity:0.95, depthWrite:false}));
chip.add(particles);
const flows = []; for (let i=0;i<NSM;i++) for (let k=0;k<PER;k++) flows.push({i, u:Math.random(), back: k%2 === 1, j:[Math.random()-.5, Math.random()-.5]});

// ---------- balloons ----------
const sp0 = () => smParts[0];
const wp = (o, x=0, y=0, z=0) => { const v = new THREE.Vector3(x,y,z); o.updateMatrixWorld(); return o.localToWorld(v); };
const PARTS = [
  [1,'Streaming multiprocessor', () => wp(smParts[1].g, -1.9, 0.3, 2.5)],
  [2,'CUDA cores', () => wp(sp0().g, -0.6, 0.5, -0.1)],
  [3,'Tensor cores', () => wp(sp0().tensors[0], 0, 0, 0).add(new THREE.Vector3(-0.5, 0.9, -0.3))],
  [4,'RT core', () => wp(smParts[3].g, 0, 0.9, 3.0)],
  [5,'Warp scheduler', () => wp(smParts[2].g, 1.0, 0.6, 2.2)],
  [6,'Register file', () => wp(smParts[2].g, -1.55, 0.7, -1.2)],
  [7,'L1 / shared memory', () => wp(smParts[3].g, 1.6, 0.7, -2.9)],
  [8,'L2 cache', () => new THREE.Vector3(5, TOP + 0.5, 0)],
  [9,'Memory controller', () => new THREE.Vector3(15, TOP + 0.6, 0)],
  [10,'HBM stack', () => new THREE.Vector3(23, 2.8, -9)],
  [11,'Silicon interposer', () => new THREE.Vector3(18, -1.6, 17)],
  [12,'Power delivery', () => new THREE.Vector3(10, 0, 27)]
];
const balEls = {};
PARTS.forEach(([n,name], idx) => { const d = document.createElement('div'); d.className = 'bal'; const b = document.createElement('b'); b.textContent = n; const s = document.createElement('span'); s.textContent = name; d.append(b, s); (idx < 6 ? $('balL') : $('balR')).append(d); balEls[n] = d; });
const svg = $('leaders');
const leaderEls = PARTS.map(() => { const l = document.createElementNS('http://www.w3.org/2000/svg','path'); l.setAttribute('fill','none'); l.setAttribute('stroke','#1c1d1f'); l.setAttribute('stroke-width','1'); const dot = document.createElementNS('http://www.w3.org/2000/svg','circle'); dot.setAttribute('r','2.4'); dot.setAttribute('fill','#1c1d1f'); svg.append(l, dot); return {l, dot}; });
function updateLeaders(){
  const wrap = $('viewWrap').getBoundingClientRect();
  PARTS.forEach(([n,,fn], idx) => {
    const on = S.show.labels && (S.show.pkg || n < 10); balEls[n].style.visibility = on ? 'visible' : 'hidden';
    const {l, dot} = leaderEls[idx]; l.style.display = dot.style.display = on ? '' : 'none'; if (!on) return;
    const v = fn().project(camera); const px = (v.x*0.5+0.5)*wrap.width, py = (-v.y*0.5+0.5)*wrap.height;
    const b = balEls[n].querySelector('b').getBoundingClientRect(); const left = idx < 6;
    const bx = (left ? b.right : b.left) - wrap.left, by = b.top + b.height/2 - wrap.top, kx = bx + (left ? 18 : -18);
    l.setAttribute('d', `M${bx},${by} L${kx},${by} L${px},${py}`); dot.setAttribute('cx', px); dot.setAttribute('cy', py);
  });
}

// ---------- UI ----------
const slist = $('slist');
STAGES.forEach((st, k) => { const b = document.createElement('button'); b.dataset.s = k; const sw = document.createElement('i'); sw.className = 'sw'; sw.style.background = k === 2 ? 'linear-gradient(90deg,#c48a1c 50%,#d2402a 50%)' : st.col; const nm = document.createElement('span'); nm.textContent = (k+1) + '. ' + st.name + ' · ' + st.nick; const dg = document.createElement('span'); dg.className = 'deg'; dg.textContent = ['1–2 cyc','1 cyc','3–6 cyc','1–10 cyc'][k]; b.append(sw, nm, dg); b.onclick = () => jumpTo(k, 1); slist.append(b); });
function jumpTo(s, dir){
  const segs = sched[S.follow].segs, t = ((Math.floor(S.cyc) % CYC) + CYC) % CYC, base = S.cyc - t;
  const order = dir > 0 ? segs.filter(g => g.a > t).concat(segs.map(g => Object.assign({}, g, {a:g.a+CYC}))) : segs.filter(g => g.a < t - 0.5).reverse().concat(segs.map(g => Object.assign({}, g, {a:g.a-CYC})).reverse());
  const hit = order.find(g => s === null ? g.s >= 0 : g.s === s); if (hit) S.cyc = base + hit.a + 0.2;
}
$('bNext').onclick = () => { S.playing = false; syncPlay(); jumpTo(null, 1); };
$('bBack').onclick = () => { S.playing = false; syncPlay(); jumpTo(null, -1); };
function syncPlay(){ $('bPlay').textContent = S.playing ? 'Pause' : 'Play'; $('bPlay').setAttribute('aria-pressed', String(S.playing)); }
$('bPlay').onclick = () => { S.playing = !S.playing; syncPlay(); };
document.querySelectorAll('[data-speed]').forEach(b => b.onclick = () => { S.speed = +b.dataset.speed; document.querySelectorAll('[data-speed]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
$('load').oninput = e => { S.target = e.target.value/100; };
[['tgPkg','pkg'],['tgFlow','flow'],['tgLabels','labels'],['tgOrbit','orbit']].forEach(([id,k]) => $(id).onclick = () => { S.show[k] = !S.show[k]; $(id).setAttribute('aria-pressed', String(S.show[k])); });

let drag = null; const pinch = new Map();
canvas.addEventListener('pointerdown', e => { e.preventDefault(); canvas.setPointerCapture(e.pointerId); pinch.set(e.pointerId, [e.clientX, e.clientY]); drag = {x:e.clientX, y:e.clientY, az:orbit.az, el:orbit.el}; });
canvas.addEventListener('pointermove', e => {
  if (!pinch.has(e.pointerId)) return; const prev = pinch.get(e.pointerId); pinch.set(e.pointerId, [e.clientX, e.clientY]);
  if (pinch.size === 2){ const [a,b] = [...pinch.values()]; const d = Math.hypot(a[0]-b[0], a[1]-b[1]); const o = [...pinch.keys()].find(k => k !== e.pointerId); const q = pinch.get(o); const d0 = Math.hypot(prev[0]-q[0], prev[1]-q[1]); orbit.dist = Math.min(260, Math.max(60, orbit.dist*d0/d)); return; }
  if (drag){ orbit.az = drag.az - (e.clientX - drag.x)*0.008; orbit.el = Math.min(1.45, Math.max(0.1, drag.el + (e.clientY - drag.y)*0.006)); }
});
['pointerup','pointercancel'].forEach(t => canvas.addEventListener(t, e => { pinch.delete(e.pointerId); if (!pinch.size) drag = null; }));
canvas.addEventListener('wheel', e => { e.preventDefault(); orbit.dist = Math.min(260, Math.max(60, orbit.dist*(1 + e.deltaY*0.001))); }, {passive:false});

// ---------- 2D canvases ----------
function setupCanvas(c){ const r = c.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio||1, 2); c.width = Math.max(10, r.width*dpr); c.height = Math.max(10, r.height*dpr); const ctx = c.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); return {ctx, w:r.width, h:r.height}; }
let TC, RC, CC;
function sizeAll(){ const r = $('viewWrap').getBoundingClientRect(); renderer.setSize(r.width, r.height, false); camera.aspect = r.width/Math.max(1, r.height); camera.updateProjectionMatrix(); svg.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`); TC = setupCanvas($('tach')); RC = setupCanvas($('radar')); CC = setupCanvas($('chart')); }
function drawGauge(){
  const {ctx,w,h} = TC; ctx.clearRect(0,0,w,h); const cx = w/2, cy = h*0.86, rad = Math.min(w*0.44, h*0.8);
  const a0 = Math.PI*1.08, a1 = Math.PI*1.92, MAXC = 3000, A = v => a0 + (a1-a0)*v/MAXC;
  ctx.lineWidth = 2; ctx.strokeStyle = '#1c1d1f'; ctx.beginPath(); ctx.arc(cx,cy,rad,a0,a1); ctx.stroke();
  ctx.strokeStyle = '#c48a1c'; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(cx,cy,rad-4,A(2200),A(2700)); ctx.stroke();
  ctx.fillStyle = '#1c1d1f'; ctx.font = '11px "Geist Mono", monospace'; ctx.textAlign = 'center';
  for (let k=0;k<=6;k++){ const a = A(k*500); ctx.lineWidth = 1.5; ctx.strokeStyle = '#1c1d1f'; ctx.beginPath(); ctx.moveTo(cx+Math.cos(a)*(rad-10), cy+Math.sin(a)*(rad-10)); ctx.lineTo(cx+Math.cos(a)*rad, cy+Math.sin(a)*rad); ctx.stroke(); ctx.fillText((k*0.5).toFixed(1), cx+Math.cos(a)*(rad-23), cy+Math.sin(a)*(rad-23)+4); }
  const a = A(S.clock); ctx.strokeStyle = '#c8371f'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx+Math.cos(a)*(rad-14), cy+Math.sin(a)*(rad-14)); ctx.stroke();
  ctx.fillStyle = '#1c1d1f'; ctx.beginPath(); ctx.arc(cx,cy,4,0,7); ctx.fill();
  const fs = Math.round(Math.max(15, Math.min(26, rad*0.2))); ctx.font = '400 '+fs+'px "Instrument Serif", serif'; ctx.fillText(Math.round(S.clock) + ' MHz', cx, cy-rad*0.12);
  ctx.font = '10px "Geist Mono", monospace'; ctx.fillStyle = '#55585c'; ctx.fillText('GHz scale', cx, cy-rad*0.12+13);
}
function metrics(){
  const s = sched[S.follow], u = S.util;
  const busy = s.segs.filter(g => g.s >= 0).reduce((a,g) => a + g.b - g.a, 0) / CYC;
  return { compute: Math.min(1, u*(1 - 0.5*s.memShare) + 0.1), bw: Math.min(1, u*(0.35 + s.memShare)*1.1),
           occ: 0.08 + 0.92*u, hit: s.hit, lat: Math.max(0.05, 1 - (1 - s.hit)*0.9 - 0.25*u), eff: Math.max(0.1, busy*(1 - 0.35*Math.max(0, u - 0.75))) };
}
function drawRadar(){
  const {ctx,w,h} = RC; ctx.clearRect(0,0,w,h); const cx = w/2, cy = h/2 + 6, rad = Math.min(w, h)*0.36;
  const m = metrics(); const axes = [['Compute', m.compute], ['Memory BW', m.bw], ['Occupancy', m.occ], ['Cache hits', m.hit], ['Low latency', m.lat], ['Work / watt', m.eff]];
  ctx.font = '10px "Geist Mono", monospace'; ctx.textAlign = 'center';
  for (let r=1;r<=4;r++){ ctx.strokeStyle = '#d9dedb'; ctx.beginPath(); axes.forEach((_,k) => { const a = -Math.PI/2 + k*2*Math.PI/axes.length; const x = cx + Math.cos(a)*rad*r/4, y = cy + Math.sin(a)*rad*r/4; k ? ctx.lineTo(x,y) : ctx.moveTo(x,y); }); ctx.closePath(); ctx.stroke(); }
  axes.forEach(([n], k) => { const a = -Math.PI/2 + k*2*Math.PI/axes.length; ctx.strokeStyle = '#d9dedb'; ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx+Math.cos(a)*rad, cy+Math.sin(a)*rad); ctx.stroke(); ctx.fillStyle = '#55585c'; ctx.fillText(n, cx+Math.cos(a)*(rad+16), cy+Math.sin(a)*(rad+14)+3); });
  ctx.beginPath(); axes.forEach(([,v], k) => { const a = -Math.PI/2 + k*2*Math.PI/axes.length; const x = cx + Math.cos(a)*rad*v, y = cy + Math.sin(a)*rad*v; k ? ctx.lineTo(x,y) : ctx.moveTo(x,y); }); ctx.closePath();
  ctx.fillStyle = 'rgba(200,55,31,0.16)'; ctx.fill(); ctx.strokeStyle = '#c8371f'; ctx.lineWidth = 1.8; ctx.stroke();
}
const segCol = g => g.s < 0 ? '#f3f1ea' : g.s === 2 && (g.kind === 'tensor' || g.kind === 'rt') ? '#d2402a' : g.s === 0 ? '#2f6fb5' : g.s === 3 ? '#8a8d90' : '#c48a1c';
const CH = {l:52, r:10, t:16, b:20};
function drawChart(){
  const {ctx,w,h} = CC; ctx.clearRect(0,0,w,h); const rowH = (h-CH.t-CH.b)/4, X = d => CH.l + d/CYC*(w-CH.l-CH.r);
  ctx.font = '10px "Geist Mono", monospace';
  for (let d=0; d<=CYC; d+=8){ ctx.strokeStyle = d%16 ? '#e8ebe9' : '#b9bdbb'; ctx.beginPath(); ctx.moveTo(X(d), CH.t-4); ctx.lineTo(X(d), h-CH.b); ctx.stroke(); ctx.fillStyle = '#55585c'; ctx.textAlign = 'center'; ctx.fillText(d, X(d), h-6); }
  for (let i=0;i<4;i++){
    const y = CH.t + i*rowH;
    sched[i].segs.forEach(g => { ctx.globalAlpha = i === S.follow ? 0.95 : 0.6; ctx.fillStyle = segCol(g); ctx.fillRect(X(g.a), y+3, X(g.b)-X(g.a), rowH-6); ctx.globalAlpha = 1;
      ctx.strokeStyle = 'rgba(28,29,31,.35)'; ctx.lineWidth = 0.6; ctx.strokeRect(X(g.a), y+3, X(g.b)-X(g.a), rowH-6);
      if (g.conflict){ ctx.fillStyle = '#1c1d1f'; ctx.textAlign = 'center'; ctx.font = '600 11px "Geist Mono", monospace'; ctx.fillText('×', X(g.b-1), y+rowH/2+4); } });
    ctx.strokeStyle = '#1c1d1f'; ctx.lineWidth = i === S.follow ? 2 : 1; ctx.strokeRect(X(0), y+3, X(CYC)-X(0), rowH-6);
    ctx.fillStyle = '#1c1d1f'; ctx.textAlign = 'left'; ctx.font = (i === S.follow ? '600 ' : '') + '11px "Geist Mono", monospace'; ctx.fillText('SM ' + i, 2, y+rowH/2+4);
  }
  const t = ((S.cyc % CYC) + CYC) % CYC; ctx.strokeStyle = '#1c1d1f'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(X(t), CH.t-8); ctx.lineTo(X(t), h-CH.b); ctx.stroke();
  ctx.fillStyle = '#1c1d1f'; ctx.beginPath(); ctx.moveTo(X(t)-5, CH.t-12); ctx.lineTo(X(t)+5, CH.t-12); ctx.lineTo(X(t), CH.t-4); ctx.fill();
}
const chart = $('chart'); let scrub = null;
function chartPos(e){ const r = chart.getBoundingClientRect(); const x = e.clientX - r.left, y = e.clientY - r.top; return {cyc: Math.min(CYC-0.01, Math.max(0, (x-CH.l)/(r.width-CH.l-CH.r)*CYC)), row: Math.floor((y-CH.t)/((r.height-CH.t-CH.b)/4)), x}; }
chart.addEventListener('pointerdown', e => { e.preventDefault(); chart.setPointerCapture(e.pointerId); const p = chartPos(e); scrub = {x:p.x, moved:false, was:S.playing}; S.playing = false; syncPlay(); S.cyc = S.cyc - (((S.cyc % CYC)+CYC)%CYC) + p.cyc; });
chart.addEventListener('pointermove', e => { if (!scrub) return; const p = chartPos(e); if (Math.abs(p.x - scrub.x) > 4) scrub.moved = true; S.cyc = S.cyc - (((S.cyc % CYC)+CYC)%CYC) + p.cyc; });
chart.addEventListener('pointerup', e => { if (!scrub) return; const p = chartPos(e); if (!scrub.moved && p.row >= 0 && p.row < 4){ S.follow = p.row; S.playing = scrub.was; syncPlay(); } scrub = null; });

// ---------- update ----------
const cTmp = new THREE.Color();
let lastKey = '';
function update(dt){
  S.util += (S.target - S.util) * Math.min(1, dt*0.9);
  const boost = 1410 + 1110*Math.min(1, S.util/0.6);
  S.power = 70 + S.util*380;
  const tgtClock = S.power > 380 ? boost - (S.power - 380)*3.2 : boost;
  S.clock += (tgtClock - S.clock) * Math.min(1, dt*1.4);
  if (Math.abs(S.util - builtLoad) > 0.08 || (Math.abs(S.util - S.target) < 0.01 && Math.abs(S.util - builtLoad) > 0.02)){ builtLoad = Math.round(S.util*20)/20; rebuild(builtLoad); }
  if (S.playing && !scrub) S.cyc += BASE_RATE*S.speed*dt*(S.clock/2500);
  if (S.show.orbit && !drag) orbit.az += dt*0.16;
  const memLoad = S.util*0.75 + 0.1;
  S.hbm += (memLoad - S.hbm) * Math.min(1, dt*0.5);
  pkg.visible = S.show.pkg;
  const tcyc = S.cyc;
  smParts.forEach((p, i) => {
    const g = segAt(i, tcyc), t = ((tcyc % CYC) + CYC) % CYC, prog = Math.min(1, (t - g.a)/Math.max(1, g.b - g.a));
    const tensorOn = g.s === 2 && g.kind === 'tensor', rtOn = g.s === 2 && g.kind === 'rt';
    p.tensors.forEach(tc => tc.material.emissive.setRGB(tensorOn ? 0.85 : 0, tensorOn ? 0.22 : 0, tensorOn ? 0.1 : 0));
    p.rtMat.emissive.setRGB(rtOn ? 0.85 : 0, rtOn ? 0.22 : 0, rtOn ? 0.1 : 0);
    // packet path inside the SM by stage
    const L1 = [0, 1.0, -p.dir*2.9], SCH = [0, 1.0, p.dir*0.95*-1 + 0], EXE = g.kind === 'tensor' ? [0.6, 1.4, 0] : g.kind === 'rt' ? [0, 1.3, p.dir*3.0] : [-0.2, 1.0, 0.1], WB = g.kind === 'mem' ? [0, 1.0, -p.dir*3.6] : [-1.5, 1.1, 0];
    const path = g.s === 0 ? [L1, SCH] : g.s === 1 ? [SCH, EXE] : g.s === 2 ? [EXE, EXE] : g.s === 3 ? [EXE, WB] : [SCH, SCH];
    const k = g.s === 2 ? 0 : prog; const a = path[0], b = path[1];
    p.packet.position.set(p.x + a[0] + (b[0]-a[0])*k, TOP + a[1] + (b[1]-a[1])*k + (g.s === 2 ? 0.25*Math.sin(t*3) : 0), p.z + a[2] + (b[2]-a[2])*k);
    p.packet.material.color.set(segCol(g)); p.packet.visible = S.show.flow && g.s >= 0;
  });
  // CUDA core activity
  for (let c=0;c<coreIndex.length;c++){ const g = segAt(coreIndex[c], tcyc); const on = g.s === 2 && g.kind === 'alu' && ((c*7 + Math.floor(tcyc)) % 3 !== 0); cores.setColorAt(c, on ? coreHot : coreBase); }
  cores.instanceColor.needsUpdate = true;
  hbmMats.forEach(m => { const hv = Math.max(0, Math.min(1, (S.hbm - 0.3)/0.6)); m.emissive.setRGB(0.7*hv, 0.2*hv, 0.05*hv); m.color.setRGB(0.85 + 0.1*hv, 0.85 - 0.3*hv, 0.84 - 0.45*hv); });
  // memory particles: flow while an SM is in a memory writeback
  particles.visible = nocLines.visible = S.show.flow;
  if (S.show.flow){
    const rate = (S.playing ? BASE_RATE*S.speed*(S.clock/2500) : 0) * 0.02;
    flows.forEach((f, k) => {
      const g = segAt(f.i, tcyc), active = g.s === 3 && g.kind === 'mem' && !g.hit, o = k*3;
      if (!active && f.u > 0.97){ pPos[o+1] = -999; return; }
      f.u += dt*rate*(active ? 1 : 0.4)*(0.7 + 0.6*Math.abs(f.j[0]))*(0.5 + S.util); if (!(f.u >= 0)) f.u = 0;
      if (f.u >= 1){ if (!active){ f.u = 0.98; pPos[o+1] = -999; return; } f.u %= 1; }
      const c = nocCurves[f.i].getPointAt(f.back ? 1 - f.u : f.u);
      pPos[o] = c.x + f.j[0]*0.5; pPos[o+1] = c.y + 0.3; pPos[o+2] = c.z + f.j[1]*0.5;
      if (f.back){ pCol[o]=0.18; pCol[o+1]=0.44; pCol[o+2]=0.71; } else { pCol[o]=0.54; pCol[o+1]=0.55; pCol[o+2]=0.56; }
    });
    pGeo.attributes.position.needsUpdate = true; pGeo.attributes.color.needsUpdate = true;
  }
  // panels
  const g = segAt(S.follow, tcyc), st = g.s >= 0 ? STAGES[g.s] : STALL;
  const key = g.s + '|' + (g.kind||'');
  if (key !== lastKey){ lastKey = key;
    $('sNum').textContent = g.s >= 0 ? g.s + 1 : '0'; $('sName').textContent = st.name;
    $('sNick').textContent = '“' + st.nick + '”'; $('sNick').style.color = segCol(g) === '#f3f1ea' ? '#55585c' : segCol(g); $('sText').textContent = st.text;
    slist.querySelectorAll('button').forEach(b => b.setAttribute('aria-current', String(+b.dataset.s === g.s))); }
  $('followLab').textContent = 'Following SM ' + S.follow + ' · ' + PROFILE[S.follow].name + ' work';
  $('rCyc').textContent = Math.floor(tcyc) + ' (' + Math.floor(((tcyc%CYC)+CYC)%CYC) + '/64)';
  $('rKind').textContent = g.s >= 0 ? KIND[g.kind] + (g.conflict ? ' · bank conflict' : '') + (g.s === 3 && g.kind === 'mem' ? (g.hit ? ' · L1 hit' : ' · miss → HBM') : '') : 'none (stall)';
  const warps = Math.round(4 + S.util*44); $('rOcc').textContent = Math.round(warps/48*100) + '%'; $('rWarps').textContent = warps + ' / 48';
  $('rHit').textContent = Math.round(sched[S.follow].hit*100) + '%'; $('rPow').textContent = Math.round(S.power) + ' W';
}
function draw(){ placeCam(); renderer.render(scene, camera); updateLeaders(); drawGauge(); drawRadar(); drawChart(); }

sizeAll(); window.addEventListener('resize', sizeAll);
if (document.fonts) document.fonts.ready.then(sizeAll);
let last = performance.now();
function frame(now){ const dt = Math.max(0, Math.min(0.05, (now-last)/1000)); last = now; update(dt); draw(); requestAnimationFrame(frame); }
if (RECORD){ window.__engine = { advance(dt){ update(dt); draw(); }, state: S, resize: sizeAll }; update(0); draw(); }
else requestAnimationFrame(frame);
})();
