(function(){
'use strict';
const $ = id => document.getElementById(id);
const SHORT = location.hash === '#short';
const RECORD = location.hash === '#record' || SHORT;
if (SHORT) document.body.classList.add('short');
const DEG = Math.PI/180;

// ---------- geometry ----------
// Double cone x² + z² = (y·tanα)², apex at the origin, axis = y. Cutting plane y = d + x·tanβ (tilt β about the z axis).
// In plane coordinates (u along the tilt, w along z) a point is (u cosβ, d + u sinβ, w) and the cut is
//   A·u² − 2 d t² sinβ·u + w² − d² t² = 0,  A = cos²β − t² sin²β,  t = tanα.
// A > 0 ellipse, A = 0 parabola, A < 0 hyperbola; eccentricity e = sinβ / cosα.
const ALPHA = 30*DEG, T = Math.tan(ALPHA), HN = 14;             // cone half-angle and nappe height
const S = { beta:0, bt:0, d:4, dt:4, ph:0, playing:true, step:0, spheres:false, labels:true, orbit:false, type:'circle', e:0, a:0, b:0, check:0, dirty:true };
function conic(beta, d){
  const sb = Math.sin(beta), cb = Math.cos(beta), A = cb*cb - T*T*sb*sb, e = sb/Math.cos(ALPHA);
  const out = {A, e, sb, cb};
  if (Math.abs(A) < 1e-9){ out.type = 'parabola'; out.p = d*T*T*sb/2; out.uv = -d/(2*sb); return out; }
  out.u0 = d*T*T*sb/A; const R = d*d*T*T*cb*cb/A;
  if (A > 0){ out.type = beta < 1e-6 ? 'circle' : 'ellipse'; out.a = Math.sqrt(R/A); out.b = Math.sqrt(R); }
  else { out.type = 'hyperbola'; out.a = Math.sqrt(R/A); out.b = Math.sqrt(-R); }
  return out;
}
// Dandelin spheres: centre (0,c,0), radius |c| sinα, tangent to the plane; they touch it at the foci.
function dandelin(beta, d){
  const cb = Math.cos(beta), sa = Math.sin(ALPHA), n = new THREE.Vector3(-Math.sin(beta), cb, 0), out = [];
  for (const den of [cb + sa, cb - sa]){
    if (Math.abs(den) < 1e-6) continue;
    const c = d*cb/den, F = new THREE.Vector3(0, c, 0).addScaledVector(n, -(c - d)*cb);
    out.push({c, r:Math.abs(c)*sa, F, u:F.x/cb});
  }
  return out;
}
const toWorld = (u, w, beta, d) => new THREE.Vector3(u*Math.cos(beta), d + u*Math.sin(beta), w);
// sample the cut as world-space polylines (split where it leaves the drawn cone)
function samples(K, beta, d){
  const lines = [], cur = [], push = p => { if (Math.abs(p.y) <= HN && p.y*1 === p.y) cur.push(p); else if (cur.length){ lines.push(cur.splice(0)); } };
  const flush = () => { if (cur.length > 1) lines.push(cur.splice(0)); else cur.length = 0; };
  if (K.type === 'circle' || K.type === 'ellipse'){ for (let i=0;i<=240;i++){ const th = i/240*Math.PI*2; push(toWorld(K.u0 + K.a*Math.cos(th), K.b*Math.sin(th), beta, d)); } flush(); }
  else if (K.type === 'parabola'){ for (let i=0;i<=300;i++){ const w = -14 + i/300*28; push(toWorld(K.uv + w*w/(4*K.p), w, beta, d)); } flush(); }
  else for (const sg of [1, -1]){ for (let i=0;i<=300;i++){ const s = -3.2 + i/300*6.4; push(toWorld(K.u0 + sg*K.a*Math.cosh(s), K.b*Math.sinh(s), beta, d)); } flush(); }
  return lines.filter(l => l.length > 1);
}

// ---------- steps ----------
const STEPS = [
  {name:'Circle', nick:'plane flat', tilt:0, spheres:false,
   text:'Cut the cone straight across. Every point of the cut is the same distance from the axis, so you get a circle. Eccentricity e = 0.'},
  {name:'Ellipse', nick:'tilt a little', tilt:35, spheres:false,
   text:'Tilt the plane and the circle stretches into an ellipse. It stays closed while the plane is flatter than the side of the cone. Here e is between 0 and 1.'},
  {name:'Parabola', nick:'parallel to the side', tilt:60, spheres:false,
   text:'Tilt until the plane runs exactly parallel to the side of the cone: 60° here, because the cone’s half-angle is 30°. The curve never closes. That is a parabola, e = 1.'},
  {name:'Hyperbola', nick:'steeper than the side', tilt:75, spheres:false,
   text:'Tilt further and the plane cuts both halves of the double cone. You get two branches: a hyperbola, e greater than 1.'},
  {name:'Where foci come from', nick:'Dandelin spheres', tilt:25, spheres:true,
   text:'Drop two balls into the cone so each touches the cone and the plane. They touch the plane exactly at the two foci. For every point P on the ellipse, PF₁ + PF₂ stays the same: 2a.'},
  {name:'One number', nick:'eccentricity', tilt:75, spheres:true,
   text:'e = sin(tilt) ÷ cos(30°). One number tells you the curve: 0 circle, below 1 ellipse, exactly 1 parabola, above 1 hyperbola. For the hyperbola, PF₁ − PF₂ stays at 2a.'}
];
function goStep(k, apply = true){ S.step = (k + STEPS.length) % STEPS.length; const s = STEPS[S.step];
  $('sNum').textContent = S.step + 1; $('sName').textContent = s.name; $('sNick').textContent = '“' + s.nick + '”'; $('sText').textContent = s.text;
  $('slist').querySelectorAll('button').forEach(b => b.setAttribute('aria-current', String(+b.dataset.k === S.step)));
  if (apply){ setTilt(s.tilt); setSpheres(s.spheres); } }
STEPS.forEach((s, k) => { const b = document.createElement('button'); b.dataset.k = k; b.innerHTML = `<span class="sw" style="background:${['#fff','#f3c9bf','#c8371f','#7a1f10','#2f6fb5','#1c1d1f'][k]}"></span><span>${k+1}. ${s.name}</span><span class="deg">${s.nick}</span>`; b.onclick = () => goStep(k); $('slist').append(b); });
const stepFor = deg => deg < 0.25 ? 0 : deg < 59.75 ? 1 : deg <= 60.25 ? 2 : 3;
function setTilt(deg){ S.bt = deg*DEG; $('tilt').value = deg; }
function setSpheres(on){ S.spheres = on; $('tgSpheres').setAttribute('aria-pressed', String(on)); }
$('tilt').oninput = e => { let v = +e.target.value; if (Math.abs(v - 60) < 0.75) v = 60; if (v < 0.75) v = 0; S.bt = v*DEG; };
$('tilt').onchange = () => { const k = stepFor(S.bt/DEG); if (S.step < 4) goStep(k, false); };
$('hgt').oninput = e => { S.dt = +e.target.value; };
document.querySelectorAll('[data-tilt]').forEach(b => b.onclick = () => { setTilt(+b.dataset.tilt); if (S.step < 4) goStep(stepFor(+b.dataset.tilt), false); });
$('tgSpheres').onclick = () => { setSpheres(!S.spheres); if (S.spheres) goStep(4, false); };
$('tgLabels').onclick = () => { S.labels = !S.labels; $('tgLabels').setAttribute('aria-pressed', String(S.labels)); };
$('tgOrbit').onclick = () => { S.orbit = !S.orbit; $('tgOrbit').setAttribute('aria-pressed', String(S.orbit)); };
$('bNext').onclick = () => goStep(S.step + 1); $('bBack').onclick = () => goStep(S.step - 1);
$('bPlay').onclick = () => { S.playing = !S.playing; $('bPlay').textContent = S.playing ? 'Pause P' : 'Move P'; $('bPlay').setAttribute('aria-pressed', String(S.playing)); };

// ---------- 3D scene ----------
const canvas = $('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true, preserveDrawingBuffer: RECORD});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 900);
const target = new THREE.Vector3(0, SHORT ? 2.5 : 1.5, 0);
const orbit = { az: 0.55, el: 0.42, dist: SHORT ? 60 : 78 };
const camF = {y:target.y, k:1};
function placeCam(){ target.y = camF.y; const fit = Math.max(1, 1.0/Math.max(0.3, camera.aspect)); const d = orbit.dist*camF.k*fit, c = Math.cos(orbit.el);
  camera.position.set(target.x + d*c*Math.sin(orbit.az), target.y + d*Math.sin(orbit.el), target.z + d*c*Math.cos(orbit.az)); camera.lookAt(target); }
scene.add(new THREE.AmbientLight(0xffffff, 0.62));
const sun = new THREE.DirectionalLight(0xffffff, 0.7); sun.position.set(-30, 60, 50); scene.add(sun);
const grad = new THREE.DataTexture(new Uint8Array([150,150,150,255, 205,205,205,255, 255,255,255,255]), 3, 1, THREE.RGBAFormat);
grad.minFilter = grad.magFilter = THREE.NearestFilter; grad.needsUpdate = true;
const INK = new THREE.LineBasicMaterial({color:0x1c1d1f});
// double cone: translucent skin, ink rims and generator lines
const coneMat = new THREE.MeshToonMaterial({color:0xd9dcd6, gradientMap:grad, transparent:true, opacity:0.32, side:THREE.DoubleSide, depthWrite:false});
const R = HN*T;
for (const sg of [1, -1]){
  const g = new THREE.ConeGeometry(R, HN, 64, 1, true); const m = new THREE.Mesh(g, coneMat);
  if (sg > 0) m.rotation.x = Math.PI; m.position.y = sg*HN/2; scene.add(m);
  const rim = []; for (let i=0;i<=64;i++){ const a = i/64*Math.PI*2; rim.push(new THREE.Vector3(R*Math.cos(a), sg*HN, R*Math.sin(a))); }
  scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(rim), INK));
}
const gen = []; for (let i=0;i<12;i++){ const a = i/12*Math.PI*2; gen.push(new THREE.Vector3(R*Math.cos(a), HN, R*Math.sin(a)), new THREE.Vector3(-R*Math.cos(a), -HN, -R*Math.sin(a))); }
scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(gen), new THREE.LineBasicMaterial({color:0x8a8d90, transparent:true, opacity:0.55})));
const axis = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,-HN-1.5,0), new THREE.Vector3(0,HN+1.5,0)]), new THREE.LineDashedMaterial({color:0x55585c, dashSize:0.5, gapSize:0.35}));
axis.computeLineDistances(); scene.add(axis);
// cutting plane: u in [-11, 11], w in [-8, 8]
const PU = 15, PW = 10;
const plane = new THREE.Group(); scene.add(plane);
const pGeo = new THREE.PlaneGeometry(PU*2, PW*2).rotateX(-Math.PI/2);
plane.add(new THREE.Mesh(pGeo, new THREE.MeshBasicMaterial({color:0x2f6fb5, transparent:true, opacity:0.12, side:THREE.DoubleSide, depthWrite:false})));
const pEdge = new THREE.LineSegments(new THREE.EdgesGeometry(pGeo), new THREE.LineDashedMaterial({color:0x2f6fb5, dashSize:0.6, gapSize:0.4})); pEdge.computeLineDistances(); plane.add(pEdge);
// cut curve as tubes, rebuilt when the plane moves
const curveMat = new THREE.MeshBasicMaterial({color:0xc8371f});
let curveMeshes = [];
// Dandelin spheres, their touching rings, the foci and the moving point P
const sphMat = new THREE.MeshToonMaterial({color:0x7fa9dc, gradientMap:grad, transparent:true, opacity:0.45, depthWrite:false});
const sph = [0,1].map(() => { const m = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 20), sphMat); scene.add(m);
  const ring = new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({length:65}, (_, i) => new THREE.Vector3(Math.cos(i/64*Math.PI*2), 0, Math.sin(i/64*Math.PI*2)))), new THREE.LineBasicMaterial({color:0x2f6fb5})); scene.add(ring);
  const f = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), new THREE.MeshBasicMaterial({color:0x2f6fb5})); scene.add(f); return {m, ring, f}; });
const P = new THREE.Mesh(new THREE.SphereGeometry(0.26, 16, 12), new THREE.MeshBasicMaterial({color:0x1c1d1f})); scene.add(P);
const pLines = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineDashedMaterial({color:0x1c1d1f, dashSize:0.35, gapSize:0.25}));
scene.add(pLines);

let K = conic(0, 4), D = dandelin(0, 4);
function rebuild(){
  K = conic(S.beta, S.d); D = dandelin(S.beta, S.d);
  curveMeshes.forEach(m => { scene.remove(m); m.geometry.dispose(); }); curveMeshes = [];
  for (const pts of samples(K, S.beta, S.d)){
    const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), Math.min(400, pts.length*2), 0.12, 6, false); const m = new THREE.Mesh(g, curveMat); scene.add(m); curveMeshes.push(m);
  }
  plane.rotation.z = S.beta; plane.position.set(0, S.d, 0);
  S.type = K.type; S.e = K.e; S.a = K.a || 0; S.b = K.b || 0;
}
// the moving point P, in plane coordinates, on the branch nearest the upper nappe
function pointP(){
  const ph = S.ph;
  if (K.type === 'circle' || K.type === 'ellipse') return {u:K.u0 + K.a*Math.cos(ph), w:K.b*Math.sin(ph)};
  if (K.type === 'parabola'){ const w = Math.sin(ph)*1.5*S.d; return {u:K.uv + w*w/(4*K.p), w}; }
  const s = Math.sin(ph)*1.1, sg = (S.d + (K.u0 + K.a)*Math.sin(S.beta)) > (S.d + (K.u0 - K.a)*Math.sin(S.beta)) ? 1 : -1;
  return {u:K.u0 + sg*K.a*Math.cosh(s), w:K.b*Math.sinh(s)};
}

// balloons
const balEls = {}, leaderEls = [], svg = $('leaders');
const LABS = [['1','Double cone'], ['2','Cutting plane'], ['3','The cut'], ['4','Focus'], ['5','Point P']];
LABS.forEach(([n,name], idx) => { const d = document.createElement('div'); d.className = 'bal'; const b = document.createElement('b'); b.textContent = n; const s = document.createElement('span'); s.textContent = name; s.id = 'bal' + n; d.append(b, s); (idx < 3 ? $('balL') : $('balR')).append(d); balEls[n] = d;
  const l = document.createElementNS('http://www.w3.org/2000/svg','path'); l.setAttribute('fill','none'); l.setAttribute('stroke','#1c1d1f'); l.setAttribute('stroke-width','1');
  const dot = document.createElementNS('http://www.w3.org/2000/svg','circle'); dot.setAttribute('r','3'); dot.setAttribute('fill','#1c1d1f'); svg.append(l, dot); leaderEls.push({l, dot}); });
function anchors(){
  const pp = pointP(), cutPt = (() => { const th = 0.9; if (K.type === 'parabola') return toWorld(K.uv + 4/(4*K.p), -2, S.beta, S.d); if (K.type === 'hyperbola') return toWorld(pointP().u, pointP().w, S.beta, S.d); return toWorld(K.u0 + K.a*Math.cos(th+2), K.b*Math.sin(th+2), S.beta, S.d); })();
  return [new THREE.Vector3(-R*0.62, HN*0.7, R*0.3), toWorld(-PU*0.8, PW*0.75, S.beta, S.d), cutPt, D[0] ? D[0].F.clone() : null, toWorld(pp.u, pp.w, S.beta, S.d)];
}
function updateLeaders(){
  const wrap = $('viewWrap').getBoundingClientRect(), A = anchors();
  $('bal3').textContent = K.type[0].toUpperCase() + K.type.slice(1);
  LABS.forEach(([n], idx) => {
    const p = A[idx], on = S.labels && p && (idx !== 3 || S.spheres); balEls[n].style.visibility = on ? 'visible' : 'hidden';
    const {l, dot} = leaderEls[idx]; l.style.display = dot.style.display = on ? '' : 'none'; if (!on) return;
    const v = p.clone().project(camera); const px = (v.x*0.5+0.5)*wrap.width, py = (-v.y*0.5+0.5)*wrap.height;
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
  if (pinch.size === 2){ const [a,b] = [...pinch.values()]; const d = Math.hypot(a[0]-b[0], a[1]-b[1]); const o = [...pinch.keys()].find(k => k !== e.pointerId); const q = pinch.get(o); const d0 = Math.hypot(prev[0]-q[0], prev[1]-q[1]); orbit.dist = Math.min(160, Math.max(30, orbit.dist*d0/d)); return; }
  if (drag){ orbit.az = drag.az - (e.clientX - drag.x)*0.008; orbit.el = Math.min(1.4, Math.max(-0.6, drag.el + (e.clientY - drag.y)*0.006)); }
});
['pointerup','pointercancel'].forEach(t => canvas.addEventListener(t, e => { pinch.delete(e.pointerId); if (!pinch.size) drag = null; }));
canvas.addEventListener('wheel', e => { e.preventDefault(); orbit.dist = Math.min(160, Math.max(30, orbit.dist*(1 + e.deltaY*0.001))); }, {passive:false});

// ---------- 2D canvases ----------
function setupCanvas(c){ const r = c.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio||1, 2); c.width = Math.max(10, r.width*dpr); c.height = Math.max(10, r.height*dpr); const ctx = c.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); return {ctx, w:r.width, h:r.height}; }
let FC, CC;
function sizeAll(){ const r = $('viewWrap').getBoundingClientRect(); renderer.setSize(r.width, r.height, false); camera.aspect = r.width/Math.max(1, r.height); camera.updateProjectionMatrix(); svg.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`); FC = setupCanvas($('face')); CC = setupCanvas($('chart')); }
const f2 = x => (Math.round(x*100 + 1e-7)/100).toFixed(2);
const same = (x, y) => Math.abs(x - y) < 1e-6 ? y : x;   // measured value equal to theory within float error: print the same digits
function drawFace(){
  const {ctx,w,h} = FC; ctx.clearRect(0,0,w,h);
  const cx0 = K.type === 'parabola' ? K.uv + 0.9*S.d : K.u0, span = (K.type === 'circle' || K.type === 'ellipse') ? Math.max(2.5, K.a*1.8) : 2.6*S.d, sc = Math.min(w, h*1.6)/(2*span), X = u => w/2 + (u - cx0)*sc, Y = v => h/2 - v*sc;
  ctx.strokeStyle = '#e1e5e3'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, h/2); ctx.lineTo(w, h/2); ctx.moveTo(X(K.type === 'parabola' ? K.uv : K.u0), 0); ctx.lineTo(X(K.type === 'parabola' ? K.uv : K.u0), h); ctx.stroke();
  ctx.strokeStyle = '#c8371f'; ctx.lineWidth = 2.4; ctx.beginPath(); let st = false;
  const pt = (u, v) => { st ? ctx.lineTo(X(u), Y(v)) : ctx.moveTo(X(u), Y(v)); st = true; };
  if (K.type === 'circle' || K.type === 'ellipse') for (let i=0;i<=200;i++){ const th = i/200*Math.PI*2; pt(K.u0 + K.a*Math.cos(th), K.b*Math.sin(th)); }
  else if (K.type === 'parabola') for (let i=0;i<=200;i++){ const v = -span + i/200*2*span; pt(K.uv + v*v/(4*K.p), v); }
  else for (const sg of [1,-1]){ st = false; for (let i=0;i<=200;i++){ const s = -3 + i/200*6; pt(K.u0 + sg*K.a*Math.cosh(s), K.b*Math.sinh(s)); } }
  ctx.stroke();
  const pp = pointP(), fu = D.map(x => x.u);
  if (K.type === 'parabola'){ const dx = X(K.uv - K.p); ctx.strokeStyle = '#2f6fb5'; ctx.setLineDash([5,4]); ctx.beginPath(); ctx.moveTo(dx, 0); ctx.lineTo(dx, h); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#2f6fb5'; ctx.font = '10px "Geist Mono", monospace'; ctx.fillText('directrix', dx + 4, 12); }
  ctx.strokeStyle = '#1c1d1f'; ctx.lineWidth = 1; ctx.setLineDash([4,3]); ctx.beginPath();
  if (K.type === 'parabola'){ ctx.moveTo(X(fu[0]), Y(0)); ctx.lineTo(X(pp.u), Y(pp.w)); ctx.lineTo(X(K.uv - K.p), Y(pp.w)); }
  else if (K.type !== 'circle'){ ctx.moveTo(X(fu[0]), Y(0)); ctx.lineTo(X(pp.u), Y(pp.w)); ctx.lineTo(X(fu[1]), Y(0)); }
  ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#2f6fb5'; ctx.font = '11px "Geist Mono", monospace';
  D.forEach((f, i) => { if (K.type === 'circle' && i) return; ctx.beginPath(); ctx.arc(X(f.u), Y(0), 4, 0, 7); ctx.fill(); ctx.fillText(K.type === 'circle' ? 'centre' : 'F' + '₁₂'[i], X(f.u) + 5, Y(0) - 6); });
  ctx.fillStyle = '#1c1d1f'; ctx.beginPath(); ctx.arc(X(pp.u), Y(pp.w), 4.5, 0, 7); ctx.fill(); ctx.fillText('P', X(pp.u) + 6, Y(pp.w) - 6);
  // live check, measured from the drawn points
  let line = '';
  if (K.type === 'ellipse'){ const s = Math.hypot(pp.u - fu[0], pp.w) + Math.hypot(pp.u - fu[1], pp.w); S.check = s; line = `PF₁ + PF₂ = ${f2(same(s, 2*K.a))} = 2a`; }
  else if (K.type === 'hyperbola'){ const s = Math.abs(Math.hypot(pp.u - fu[0], pp.w) - Math.hypot(pp.u - fu[1], pp.w)); S.check = s; line = `|PF₁ − PF₂| = ${f2(same(s, 2*K.a))} = 2a`; }
  else if (K.type === 'parabola'){ const a1 = Math.hypot(pp.u - fu[0], pp.w), a2 = pp.u - (K.uv - K.p); S.check = a1 - a2; line = `PF = ${f2(same(a1, a2))} = distance to directrix ${f2(a2)}`; }
  else { const r = Math.hypot(pp.u - fu[0], pp.w); S.check = r; line = `distance to centre = ${f2(r)} = r`; }
  ctx.font = '12px "Geist Mono", monospace'; const tw = ctx.measureText(line).width; ctx.fillStyle = 'rgba(251,250,246,0.92)'; ctx.fillRect(4, h - 24, tw + 10, 20); ctx.fillStyle = '#1c1d1f'; ctx.fillText(line, 9, h - 9);
}
function eqText(){
  if (K.type === 'circle') return `x² + y² = ${f2(K.a*K.a)}   (r = ${f2(K.a)})`;
  if (K.type === 'ellipse') return `x²/${f2(K.a*K.a)} + y²/${f2(K.b*K.b)} = 1   (a = ${f2(K.a)}, b = ${f2(K.b)}, 2a = ${f2(2*K.a)})`;
  if (K.type === 'hyperbola') return `x²/${f2(K.a*K.a)} − y²/${f2(K.b*K.b)} = 1   (a = ${f2(K.a)}, b = ${f2(K.b)}, 2a = ${f2(2*K.a)})`;
  return `y² = 4ax with a = ${f2(K.p)}`;
}
function drawChart(){
  const {ctx,w,h} = CC; ctx.clearRect(0,0,w,h); const L = 30, Rr = w - 20, EMAX = 1.6, X = e => L + e/EMAX*(Rr - L), y = h*0.45;
  ctx.fillStyle = 'rgba(200,55,31,0.08)'; ctx.fillRect(X(0), y-14, X(1)-X(0), 28); ctx.fillStyle = 'rgba(47,111,181,0.08)'; ctx.fillRect(X(1), y-14, Rr - X(1), 28);
  ctx.strokeStyle = '#1c1d1f'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(L, y); ctx.lineTo(Rr, y); ctx.stroke();
  ctx.font = '11px "Geist Mono", monospace'; ctx.textAlign = 'center'; ctx.fillStyle = '#55585c';
  for (let e=0; e<=1.6001; e+=0.2){ ctx.beginPath(); ctx.moveTo(X(e), y-5); ctx.lineTo(X(e), y+5); ctx.stroke(); ctx.fillText(e.toFixed(1), X(e), y+19); }
  ctx.fillStyle = '#1c1d1f'; ctx.font = '13px "Instrument Serif", serif';
  ctx.fillText('circle  e = 0', X(0) + 34, y-22); ctx.fillText('ellipse  0 < e < 1', X(0.5), y-22); ctx.fillText('parabola  e = 1', X(1), y-22); ctx.fillText('hyperbola  e > 1', X(1.32), y-22);
  ctx.strokeStyle = '#1c1d1f'; ctx.setLineDash([3,3]); ctx.beginPath(); ctx.moveTo(X(1), y-16); ctx.lineTo(X(1), y+8); ctx.stroke(); ctx.setLineDash([]);
  const xe = X(Math.min(EMAX, S.e)); ctx.fillStyle = '#c8371f'; ctx.beginPath(); ctx.moveTo(xe, y-2); ctx.lineTo(xe-8, y-16); ctx.lineTo(xe+8, y-16); ctx.closePath(); ctx.fill();
  ctx.font = '13px "Geist Mono", monospace'; ctx.fillText('e = ' + S.e.toFixed(3), xe, y + 36);
}

// ---------- update / draw ----------
function update(dt){
  const nb = S.beta + (S.bt - S.beta)*Math.min(1, dt*4), nd = S.d + (S.dt - S.d)*Math.min(1, dt*4);
  const snapB = Math.abs(nb - S.bt) < 0.0008 ? S.bt : nb, snapD = Math.abs(nd - S.dt) < 0.002 ? S.dt : nd;
  if (snapB !== S.beta || snapD !== S.d || S.dirty){ S.beta = snapB; S.d = snapD; S.dirty = false; rebuild(); }
  if (S.playing) S.ph += dt*0.8;
  if (S.orbit) orbit.az += dt*0.25;
  if (RECORD){ S.drift = (S.drift || 0) + dt; orbit.az += dt*0.06*Math.cos(S.drift*0.21); }   // slow camera drift so held shots keep moving
  // frame what matters: the upper nappe for closed curves and the parabola, the whole double cone for the hyperbola
  const want = K.type === 'hyperbola' ? {y:1.5, k:1} : K.type === 'parabola' ? {y:S.d + 3, k:0.8} : {y:S.d + 2.5, k:0.62};
  camF.y += (want.y - camF.y)*Math.min(1, dt*2.5); camF.k += (want.k - camF.k)*Math.min(1, dt*2.5);
  $('tiltLab').textContent = (S.beta/DEG).toFixed(1) + '°'; $('hgtLab').textContent = S.d.toFixed(2);
  $('sNow').textContent = `${K.type[0].toUpperCase() + K.type.slice(1)} · e = ${S.e.toFixed(3)} · tilt ${(S.beta/DEG).toFixed(1)}°`;
  $('sEq').textContent = eqText();
}
function draw(){
  placeCam();
  D.forEach((s, i) => { const vis = S.spheres && Math.abs(s.c) < HN + 6; const o = sph[i]; o.m.visible = o.ring.visible = vis; o.f.visible = S.spheres;
    o.m.position.set(0, s.c, 0); o.m.scale.setScalar(s.r); o.ring.position.set(0, s.c*Math.cos(ALPHA)**2, 0); o.ring.scale.set(Math.abs(s.c)*Math.cos(ALPHA)*Math.sin(ALPHA), 1, Math.abs(s.c)*Math.cos(ALPHA)*Math.sin(ALPHA)); o.f.position.copy(s.F); });
  for (let i=D.length; i<2; i++){ sph[i].m.visible = sph[i].ring.visible = sph[i].f.visible = false; }
  const pp = pointP(), pw = toWorld(pp.u, pp.w, S.beta, S.d); P.position.copy(pw);
  const showL = S.spheres && K.type !== 'circle' && D.length;
  pLines.visible = !!showL;
  if (showL){ const a = D[0].F, b = K.type === 'parabola' ? toWorld(K.uv - K.p, pp.w, S.beta, S.d) : D[1].F; pLines.geometry.setFromPoints([a, pw, b]); pLines.computeLineDistances(); }
  renderer.render(scene, camera); updateLeaders(); drawFace(); drawChart();
}

goStep(0, false); rebuild(); sizeAll(); window.addEventListener('resize', sizeAll);
if (document.fonts) document.fonts.ready.then(sizeAll);
let last = performance.now();
function frame(now){ const dt = Math.max(0, Math.min(0.05, (now-last)/1000)); last = now; update(dt); draw(); requestAnimationFrame(frame); }
if (RECORD){ window.__engine = { advance(dt){ update(dt); draw(); }, step(dt){ update(dt); }, draw, state: S, resize: sizeAll }; update(0); draw(); }
else requestAnimationFrame(frame);
})();
