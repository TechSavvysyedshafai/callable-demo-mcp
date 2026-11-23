// Shared level data and physics (used by the page and by the solvability check).
const PLANETS = { Earth: 9.81, Moon: 1.62, Mars: 3.71, Jupiter: 24.79 };
const LEVELS = [
  { name: 'First shot',        planet: 'Earth',   d: 40,  h: 0,  w: 6,  y0: 0,  walls: [], guide: true,  tip: 'Range on flat ground: R = v² sin 2θ / g. 45° goes farthest.' },
  { name: 'Longer field',      planet: 'Earth',   d: 70,  h: 0,  w: 5,  y0: 0,  walls: [], guide: true,  tip: 'Double the speed and the range goes up four times (v²).' },
  { name: 'Up on the tower',   planet: 'Earth',   d: 55,  h: 10, w: 5,  y0: 0,  walls: [], guide: false, tip: 'A raised target needs a little more speed than flat ground.' },
  { name: 'Over the wall',     planet: 'Earth',   d: 60,  h: 0,  w: 6,  y0: 0,  walls: [{ x: 30, h: 15 }], guide: false, tip: 'Steeper angle, higher arch. 30° and 60° land at the same spot on flat ground.' },
  { name: 'Moon walk',         planet: 'Moon',    d: 150, h: 0,  w: 12, y0: 0,  walls: [], guide: false, tip: 'Moon gravity is about 1/6 of Earth, so the same shot flies about 6 times as far.' },
  { name: 'Red planet ledge',  planet: 'Mars',    d: 120, h: 20, w: 10, y0: 0,  walls: [], guide: false, tip: 'Mars pulls at 3.71 m/s², a bit over a third of Earth.' },
  { name: 'Tall wall',         planet: 'Earth',   d: 90,  h: 0,  w: 5,  y0: 0,  walls: [{ x: 45, h: 25 }], guide: false, tip: 'Max height H = v² sin²θ / 2g. Make H clear the wall.' },
  { name: 'Heavy world',       planet: 'Jupiter', d: 40,  h: 0,  w: 5,  y0: 0,  walls: [], guide: false, tip: 'Jupiter pulls 2.5 times harder than Earth. You need far more speed.' },
  { name: 'Steep climb',       planet: 'Earth',   d: 30,  h: 25, w: 5,  y0: 0,  walls: [], guide: false, tip: 'High and close: try a steep angle.' },
  { name: 'Lunar fortress',    planet: 'Moon',    d: 250, h: 40, w: 14, y0: 0,  walls: [{ x: 120, h: 80 }], guide: false, tip: 'Slow gravity means long flights. Watch the timer.' },
  { name: 'Double barrier',    planet: 'Mars',    d: 180, h: 0,  w: 10, y0: 0,  walls: [{ x: 60, h: 45 }, { x: 125, h: 45 }], guide: false, tip: 'Both walls have to be cleared by the same arch.' },
  { name: 'Cliff shot',        planet: 'Earth',   d: 110, h: 0,  w: 5,  y0: 30, walls: [], guide: false, tip: 'Launching from a 30 m cliff: the ball falls further, so it lands farther than R.' },
];
// One step of the flight. Returns 'hit', 'ground', 'wall', or null (still flying).
function stepShot(L, s, dt) {
  const g = PLANETS[L.planet], px = s.x, py = s.y;
  s.t += dt; s.x += s.vx * dt; s.vy -= g * dt; s.y += s.vy * dt;
  for (const w of L.walls) {
    const half = Math.max(1, L.d * 0.012);
    if (s.x >= w.x - half && s.x <= w.x + half && s.y <= w.h) return 'wall';
  }
  const tx0 = L.d - L.w / 2, tx1 = L.d + L.w / 2;
  if (L.h > 0) {               // tower: top surface is the target, sides are a miss
    if (py >= L.h && s.y < L.h) { const xc = px + (s.x - px) * (py - L.h) / (py - s.y); if (xc >= tx0 && xc <= tx1) return 'hit'; }
    if (s.x >= tx0 && s.x <= tx1 && s.y < L.h && s.y > 0) return 'wall';
  }
  if (s.y <= 0) {
    const xc = px + (s.x - px) * py / (py - s.y);
    if (L.h === 0 && xc >= tx0 && xc <= tx1) return 'hit';
    s.x = xc; s.y = 0; return 'ground';
  }
  if (s.x > L.d * 3 + 200 || s.t > 120) return 'ground';
  return null;
}
function newShot(L, angleDeg, v) {
  const a = angleDeg * Math.PI / 180;
  return { x: 0, y: L.y0, vx: v * Math.cos(a), vy: v * Math.sin(a), t: 0, maxY: L.y0 };
}
if (typeof module !== 'undefined') module.exports = { PLANETS, LEVELS, stepShot, newShot };
