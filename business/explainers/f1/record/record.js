// Records a silent 60 fps 1920x1080 walkthrough of the F1 airflow page, frame by frame,
// with a visible cursor that really clicks the controls. Writes frames/*.jpg and rpm.json.
// Usage: THREE_JS=/path/three.min.js OUT=/path/out [MODE=short] node record.js   (short = 1080x1920 vertical)
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const OUT = process.env.OUT || path.join(__dirname, 'out'); const FR = path.join(OUT, 'frames');
fs.mkdirSync(FR, {recursive:true});
const SHORT = process.env.MODE === 'short';
const PAGE = 'file://' + path.resolve(__dirname, '../index.html') + (SHORT ? '#short' : '#record');
const FPS = 60, DT = 1/FPS;
const MAX = +(process.env.MAX_FRAMES || 1e9);

// timeline: [seconds, action]
const T = [
  [1.0, {move:'[data-speed="0.0166667"]'}], [1.6, {click:'[data-speed="0.0166667"]'}],
  [4.0, {move:'#bNext'}], [4.5, {click:'#bNext'}], [6.5, {click:'#bNext'}], [8.5, {click:'#bNext'}],
  [10.0, {move:'#bPlay'}], [10.5, {click:'#bPlay'}],
  [11.2, {move:'[data-speed="0.0833333"]'}], [11.7, {click:'[data-speed="0.0833333"]'}],
  [12.5, {drag:'#speed', from:0.38, to:0.96, dur:2.0}],
  [16.0, {move:'#bDRS'}], [16.5, {click:'#bDRS'}], [19.5, {click:'#bDRS'}],
  [21.0, {move:'[data-rh="low"]'}], [21.5, {click:'[data-rh="low"]'}], [23.5, {move:'[data-rh="high"]'}], [24.0, {click:'[data-rh="high"]'}], [25.5, {move:'[data-rh="med"]'}], [26.0, {click:'[data-rh="med"]'}],
  [27.0, {orbit:'#view', dx: SHORT ? -150 : -260, dy: SHORT ? 30 : 50, dur:2.0}],
  [29.6, {scrub:'#chart', from:0.1, to:0.8, dur:2.0}],
  [32.0, {move:'#tgBody'}], [32.5, {click:'#tgBody'}], [34.0, {click:'#tgBody'}],
  [34.8, {move:'#tgOrbit'}], [35.2, {click:'#tgOrbit'}],
  [36.0, {drag:'#speed', from:0.96, to:0.45, dur:1.4}],
  [38.0, {move:'[data-speed="0.005"]'}], [38.5, {click:'[data-speed="0.005"]'}],
  [41.0, {end:true}]
];

(async () => {
  const browser = await chromium.launch({args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
  const page = await browser.newPage(SHORT ? {viewport:{width:540, height:960}, deviceScaleFactor:2} : {viewport:{width:1920, height:1080}, deviceScaleFactor:1});
  if (process.env.THREE_JS) await page.route('**/three.min.js', r => r.fulfill({path:process.env.THREE_JS, contentType:'application/javascript'}));
  await page.goto(PAGE); await page.waitForFunction(() => window.__engine); await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.evaluate(() => { window.__engine.resize();
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg width="26" height="30" viewBox="0 0 26 30"><path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 16 L21 16 Z" fill="#fff" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:99999, pointerEvents:'none', transform:'translate(270px,480px)'});
    const ring = document.createElement('div'); ring.id = '__ring';
    Object.assign(ring.style, {position:'fixed', width:'34px', height:'34px', borderRadius:'50%', border:'3px solid #c8371f', zIndex:99998, pointerEvents:'none', opacity:0});
    document.body.append(c, ring); });
  const cur = SHORT ? {x:270, y:480} : {x:960, y:540}; let tween = null, ringT = 0; const log = [];
  const center = async sel => page.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return {x:r.left+r.width/2, y:r.top+r.height/2, w:r.width, h:r.height, l:r.left, t:r.top}; }, sel);
  const ease = t => t<.5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2;
  let ti = 0, frame = 0, held = false;
  const total = Math.round(T[T.length-1][0]*FPS);
  for (frame = 0; frame < Math.min(total, MAX); frame++){
    const t = frame/FPS;
    while (ti < T.length && T[ti][0] <= t){
      const a = T[ti][1]; ti++;
      if (a.move){ const c = await center(a.move); tween = {x0:cur.x, y0:cur.y, x1:c.x, y1:c.y, t0:t, d:0.5}; }
      if (a.click){ const c = await center(a.click); cur.x = c.x; cur.y = c.y; tween = null; await page.mouse.move(cur.x, cur.y); await page.mouse.click(cur.x, cur.y); ringT = t; }
      if (a.drag){ const c = await center(a.drag); const y = c.y; const x0 = c.l + c.w*a.from, x1 = c.l + c.w*a.to; tween = {x0:cur.x,y0:cur.y,x1:x0,y1:y,t0:t,d:0.4, then:{x0, x1, y, t0:t+0.4, d:a.dur, drag:true}}; }
      if (a.orbit){ const c = await center(a.orbit); tween = {x0:cur.x,y0:cur.y,x1:c.x,y1:c.y,t0:t,d:0.4, then:{x0:c.x, x1:c.x+a.dx, y:c.y, y1:c.y+a.dy, t0:t+0.4, d:a.dur, drag:true}}; }
      if (a.scrub){ const c = await center(a.scrub); const x0 = c.l+60+(c.w-70)*a.from, x1 = c.l+60+(c.w-70)*a.to, y = c.t + c.h*0.35; tween = {x0:cur.x,y0:cur.y,x1:x0,y1:y,t0:t,d:0.4, then:{x0, x1, y, t0:t+0.4, d:a.dur, drag:true}}; }
      if (a.chartRow !== undefined){ const c = await center('#chart'); const x = c.l + c.w*0.5, y = c.t + 16 + (c.h-36)*(a.chartRow+0.5)/4; tween = {x0:cur.x,y0:cur.y,x1:x,y1:y,t0:t,d:0.5, clickAtEnd:true}; }
    }
    if (tween){
      const k = Math.min(1, (t - tween.t0)/tween.d), e = ease(k);
      if (tween.drag){
        const x = tween.x0 + (tween.x1 - tween.x0)*e, y = tween.y + ((tween.y1 ?? tween.y) - tween.y)*e;
        if (!held){ await page.mouse.move(tween.x0, tween.y); await page.mouse.down(); held = true; ringT = t; }
        cur.x = x; cur.y = y; await page.mouse.move(x, y);
        if (k >= 1){ await page.mouse.up(); held = false; tween = null; }
      } else if (t >= tween.t0) {
        cur.x = tween.x0 + (tween.x1 - tween.x0)*e; cur.y = tween.y0 + (tween.y1 - tween.y0)*e;
        if (k >= 1){ const nx = tween.then, ce = tween.clickAtEnd; tween = nx ? Object.assign({}, nx) : null; if (ce){ await page.mouse.move(cur.x, cur.y); await page.mouse.click(cur.x, cur.y); ringT = t; } }
      }
    }
    const st = await page.evaluate(([dt, x, y, rk]) => {
      window.__engine.advance(dt);
      document.getElementById('__cur').style.transform = `translate(${x}px,${y}px)`;
      const r = document.getElementById('__ring'); r.style.left = (x-17)+'px'; r.style.top = (y-17)+'px'; r.style.opacity = Math.max(0, 1-rk*3); r.style.transform = `scale(${0.6+rk*1.4})`;
      const S = window.__engine.state; return {rpm:S.rpm, thr:S.thr, util:S.util, clock:S.clock, power:S.power, v:S.v, drs:S.drs, flap:S.flap, playing:S.playing, speed:S.speed};
    }, [DT, cur.x, cur.y, held ? 0.1 : t - ringT]);
    log.push(Object.assign({t, frame}, st));
    await page.screenshot({path: path.join(FR, `f${String(frame).padStart(5,'0')}.jpg`), type:'jpeg', quality:88});
    if (frame % 120 === 0) console.log('frame', frame, 'of', total);
  }
  fs.writeFileSync(path.join(OUT, 'rpm.json'), JSON.stringify({fps:FPS, frames:log}));
  await browser.close(); console.log('done', frame, 'frames');
})();
