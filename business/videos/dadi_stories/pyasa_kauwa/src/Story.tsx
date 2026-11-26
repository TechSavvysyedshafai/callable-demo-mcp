// "Pyasa Kauwa" (The Thirsty Crow) — one continuous picture-book world, 1080x1920, 30 fps.
// Scene times match the @times in script.md (seconds). Everything is deterministic (no Math.random).
import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig, spring} from 'remotion';

const C = {ink: '#2a1d14', paper: '#fbf3e4', sky1: '#ffd08a', sky2: '#ff9d5c', ground: '#c98b4e', ground2: '#a8703c',
  clay: '#b5532e', clayD: '#8a3a1e', water: '#4aa3d8', waterD: '#2f7fb3', leaf: '#5d8f3a', leafD: '#3f6b25', crow: '#1f1f2a'};
const POT = {x: 540, y: 1060, r: 175, rim: 860, bottom: 1235};
const lerp = (t: number, a: number[], b: number[], ease = Easing.inOut(Easing.cubic)) =>
  interpolate(t, a, b, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});

// pebble k drops at this time (seconds)
const DROPS = [33.2, 34.4, 35.5, 36.6, 37.6, 38.6, 39.6, 40.6];
const PEB = [[-60, 0], [10, 6], [75, -2], [-25, -38], [45, -40], [-80, -45], [15, -78], [-45, -82]];

const Crow: React.FC<{t: number; flap: number; dip: number; happy?: boolean}> = ({t, flap, dip, happy}) => {
  const wing = Math.sin(t * Math.PI * 2 * 3) * 35 * flap;
  return (
    <g>
      <path d="M-70 -10 L-125 -35 L-118 -5 L-130 10 Z" fill={C.crow} stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
      <ellipse cx={0} cy={0} rx={78} ry={52} fill={C.crow} stroke={C.ink} strokeWidth={5} />
      <g transform={`translate(60 -38) rotate(${dip})`}>
        <circle cx={0} cy={0} r={40} fill={C.crow} stroke={C.ink} strokeWidth={5} />
        <path d="M30 -6 L92 6 L30 16 Z" fill="#e8a33c" stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
        <circle cx={12} cy={-10} r={10} fill="#fff" />
        <circle cx={15} cy={-10} r={5} fill={C.ink} />
        {happy && <path d="M2 -28 Q12 -36 24 -28" stroke="#fff" strokeWidth={4} fill="none" />}
      </g>
      <g transform={`translate(-10 -20) rotate(${-20 + wing})`}>
        <path d="M0 0 Q-60 -70 -120 -40 Q-70 -20 -10 18 Z" fill="#33334a" stroke={C.ink} strokeWidth={5} strokeLinejoin="round" />
      </g>
      <path d="M-10 48 L-14 78 M18 48 L22 78" stroke="#e8a33c" strokeWidth={6} strokeLinecap="round" />
    </g>
  );
};

export const Story: React.FC = () => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig(); const t = frame / fps;

  // sky warms up for the hot day, cools for the lesson at the end
  const heat = lerp(t, [4.5, 8, 48, 52], [0.2, 1, 1, 0]);
  const skyTop = heat > 0.5 ? C.sky2 : '#9fd3f2';
  // camera: zoom into the pot for the inside view, out again before the crow flies away
  const zoom = lerp(t, [20.3, 22.3, 46.8, 48.8], [1, 1.55, 1.55, 1]);
  const camY = lerp(t, [20.3, 22.3, 46.8, 48.8], [0, 140, 140, 0]);
  // pot pops in at 16.5 s
  const potIn = spring({frame: frame - 16.3 * fps, fps, config: {damping: 11}});
  // inside view: pot front fades to show the water
  const xray = lerp(t, [21.5, 23], [0, 0.82]) * (1 - lerp(t, [46, 47.5], [0, 1]));
  const dropped = DROPS.filter(d => t > d + 0.55).length;
  const level = POT.bottom - 50 - dropped * 34 + lerp(t, [45, 47.5], [0, 25]);   // y of the water surface
  const levelShown = lerp(t, [0, 1], [level, level]);

  // crow path
  let cx = -200, cy = 700, flap = 1, dip = 0, scale = 0.8, show = true, flip = 1;
  if (t < 5) { cx = lerp(t, [0.4, 4.6], [-200, 1280], Easing.linear); cy = 740 + Math.sin(t * 2.2) * 40; scale = 0.7; }
  else if (t < 10) { show = false; }
  else if (t < 16.5) { cx = lerp(t, [10, 14, 16.4], [-200, 880, 760]); cy = 560 + Math.sin(t * 2.5) * 70; }
  else if (t < 48.5) {
    const land = lerp(t, [16.6, 19.2], [0, 1]);
    cx = lerp(land, [0, 1], [760, 500], Easing.linear); cy = lerp(land, [0, 1], [560, POT.rim - 64], Easing.linear);
    flap = 1 - land; scale = 0.8;
    // reaching for the water and failing; later drinking
    if (t > 22.5 && t < 26.5) dip = 35 + Math.max(0, Math.sin((t - 22.5) * 4)) * 25;
    if (t > 44.6 && t < 47.6) dip = 45 + Math.abs(Math.sin((t - 44.6) * 5)) * 20;
  } else { cx = lerp(t, [48.5, 50.5], [500, 1300]); cy = lerp(t, [48.5, 50.5], [POT.rim - 64, 200]); flap = 1; }
  if (t > 50.5) show = false;

  const titleIn = lerp(t, [0.6, 1.6, 4.2, 4.9], [0, 1, 1, 0]);
  const lessonIn = lerp(t, [50.2, 51.4], [0, 1]);
  const think = lerp(t, [27.2, 28, 31.8, 32.4], [0, 1, 1, 0]);
  const bulb = spring({frame: frame - 29.4 * fps, fps, config: {damping: 9}});
  const cracks = lerp(t, [6, 9], [600, 0]);

  return (
    <AbsoluteFill style={{background: C.paper}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={skyTop} />
            <stop offset="1" stopColor={heat > 0.5 ? C.sky1 : '#e3f3fb'} />
          </linearGradient>
          <clipPath id="potIn"><circle cx={POT.x} cy={POT.y} r={POT.r - 14} /><rect x={POT.x - 62} y={POT.rim + 10} width={124} height={120} /></clipPath>
          <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={3} /><feColorMatrix values="0 0 0 0 0.4  0 0 0 0 0.3  0 0 0 0 0.2  0 0 0 0.08 0" /></filter>
        </defs>
        <g transform={`translate(${540 + Math.sin(t * 0.5) * 18} ${1000 - camY + Math.sin(t * 0.37) * 12}) scale(${zoom * (1.03 + 0.025 * Math.sin(t * 0.3))}) translate(-540 -1000)`}>
          <rect x={-300} y={-300} width={1700} height={1560} fill="url(#sky)" />
          {/* sun */}
          <g transform={`translate(850 ${300 - heat * 40}) rotate(${t * 12})`}>
            {Array.from({length: 12}).map((_, i) => (
              <rect key={i} x={-8} y={-150 - heat * 30 - Math.sin(t * 4 + i) * 10} width={16} height={50} rx={8} fill="#ffb02e" transform={`rotate(${i * 30})`} />
            ))}
            <circle r={90} fill="#ffcf3f" stroke={C.ink} strokeWidth={6} />
          </g>
          {/* heat shimmer */}
          {[0, 1, 2].map(i => (
            <path key={i} d={`M${120 + i * 300} ${1150 - i * 20} q30 -30 60 0 t60 0 t60 0`} stroke="#fff" strokeWidth={6} fill="none" strokeLinecap="round"
              opacity={heat * 0.6 * (0.5 + 0.5 * Math.sin(t * 3 + i))} transform={`translate(0 ${-((t * 30 + i * 40) % 80)})`} />
          ))}
          {/* hills and ground */}
          <path d="M-300 1200 Q100 1040 420 1180 T1400 1150 V1260 H-300 Z" fill="#d9a45f" stroke={C.ink} strokeWidth={5} />
          <rect x={-300} y={1240} width={1700} height={1000} fill={C.ground} />
          <path d="M-300 1240 H1400" stroke={C.ink} strokeWidth={6} />
          {/* dry cracks drawing in */}
          <path d="M80 1320 l60 40 l-20 50 l70 30 M820 1300 l-40 60 l50 40 l-30 60 M420 1420 l50 20 l40 -30 l60 40"
            stroke={C.ground2} strokeWidth={8} fill="none" strokeLinecap="round" strokeDasharray={600} strokeDashoffset={cracks} />
          {/* tree */}
          <g transform="translate(150 1240)">
            <path d="M-22 0 L-14 -300 Q0 -330 14 -300 L22 0 Z" fill="#7a4f2b" stroke={C.ink} strokeWidth={5} />
            <circle cx={-40} cy={-330} r={110} fill={C.leaf} stroke={C.ink} strokeWidth={5} />
            <circle cx={60} cy={-360} r={95} fill={C.leafD} stroke={C.ink} strokeWidth={5} />
            <circle cx={10} cy={-430} r={90} fill={C.leaf} stroke={C.ink} strokeWidth={5} />
          </g>
          {/* pebble pile on the ground, shrinking as pebbles are used */}
          {PEB.map(([px, py], k) => k >= dropped && (
            <ellipse key={k} cx={770 + px * 0.6} cy={1245 + py * 0.35} rx={26} ry={20} fill="#9a9a8c" stroke={C.ink} strokeWidth={4} />
          ))}
          {/* the pot */}
          <g transform={`translate(${POT.x} ${POT.bottom}) scale(${potIn}) translate(${-POT.x} ${-POT.bottom})`}>
            <ellipse cx={POT.x} cy={POT.bottom + 6} rx={150} ry={22} fill="#00000033" />
            {/* inside: water and pebbles (visible through the x-ray) */}
            <g clipPath="url(#potIn)">
              <rect x={POT.x - 200} y={POT.rim} width={400} height={420} fill="#5a2a16" />
              <rect x={POT.x - 200} y={levelShown} width={400} height={500} fill={C.water} />
              <path d={`M${POT.x - 200} ${levelShown} q25 -10 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0`} stroke="#bfe6ff" strokeWidth={6} fill="none"
                transform={`translate(${-((t * 40) % 100)} 0)`} />
              {PEB.map(([px, py], k) => {
                const d = DROPS[k]; if (t < d) return null;
                const y = lerp(t, [d, d + 0.55], [POT.rim - 40, POT.bottom - 40 + py], Easing.in(Easing.quad));
                return <ellipse key={k} cx={POT.x + px} cy={y} rx={30} ry={22} fill="#9a9a8c" stroke={C.ink} strokeWidth={4} />;
              })}
            </g>
            {/* front of the pot, fades for the inside view */}
            <g opacity={1 - xray}>
              <circle cx={POT.x} cy={POT.y} r={POT.r} fill={C.clay} stroke={C.ink} strokeWidth={6} />
              <path d={`M${POT.x - 150} ${POT.y - 20} Q${POT.x} ${POT.y + 30} ${POT.x + 150} ${POT.y - 20}`} stroke="#f2c14e" strokeWidth={10} fill="none" />
              <path d={`M${POT.x - 140} ${POT.y + 40} Q${POT.x} ${POT.y + 90} ${POT.x + 140} ${POT.y + 40}`} stroke={C.clayD} strokeWidth={8} fill="none" />
              <rect x={POT.x - 62} y={POT.rim + 10} width={124} height={70} fill={C.clay} stroke={C.ink} strokeWidth={6} />
            </g>
            <g fill="none" stroke={C.ink} strokeWidth={6}><circle cx={POT.x} cy={POT.y} r={POT.r} opacity={xray} /></g>
            <rect x={POT.x - 80} y={POT.rim} width={160} height={22} rx={10} fill={C.clayD} stroke={C.ink} strokeWidth={6} />
            {/* the gap the beak cannot cross */}
            {t > 23 && t < 27 && <path d={`M${POT.x + 45} ${POT.rim + 30} V${levelShown - 8}`} stroke="#e23b2e" strokeWidth={6} strokeDasharray="14 12" />}
          </g>
          {/* falling pebble above the rim, carried by the crow */}
          {DROPS.map((d, k) => t > d - 0.35 && t < d + 0.05 && (
            <ellipse key={k} cx={POT.x + 20} cy={lerp(t, [d - 0.35, d], [POT.rim - 120, POT.rim - 30])} rx={26} ry={20} fill="#9a9a8c" stroke={C.ink} strokeWidth={4} />
          ))}
          {show && <g transform={`translate(${cx} ${cy + Math.sin(t * 5) * 3}) scale(${scale * flip} ${scale * (1 + 0.02 * Math.sin(t * 5))})`}><Crow t={t} flap={flap} dip={dip} happy={t > 44.5} /></g>}
          {/* thought bubble */}
          <g opacity={think} transform={`translate(720 ${POT.rim - 250})`}>
            <circle cx={-150} cy={190} r={14} fill="#fff" stroke={C.ink} strokeWidth={4} />
            <circle cx={-110} cy={140} r={22} fill="#fff" stroke={C.ink} strokeWidth={4} />
            <ellipse cx={0} cy={0} rx={150} ry={110} fill="#fff" stroke={C.ink} strokeWidth={6} />
            <ellipse cx={-45} cy={20} rx={40} ry={30} fill="#9a9a8c" stroke={C.ink} strokeWidth={4} />
            <g transform={`translate(55 -10) scale(${bulb})`}>
              <circle r={40} fill="#ffd84a" stroke={C.ink} strokeWidth={5} />
              <rect x={-18} y={36} width={36} height={24} rx={4} fill="#999" stroke={C.ink} strokeWidth={4} />
            </g>
          </g>
        </g>
        <rect width={1080} height={1920} filter="url(#paper)" />
      </svg>
      {/* title card */}
      <div style={{position: 'absolute', top: 330, width: '100%', textAlign: 'center', opacity: titleIn, transform: `translateY(${(1 - titleIn) * 30}px)`,
        fontFamily: 'Noto Sans Devanagari', color: C.ink}}>
        <div style={{fontSize: 70, fontWeight: 700}}>दादी की कहानी</div>
        <div style={{fontSize: 120, fontWeight: 700, color: '#8a3a1e', marginTop: -10}}>प्यासा कौआ</div>
      </div>
      {/* lesson card */}
      <div style={{position: 'absolute', top: 250, left: 90, right: 90, padding: '40px 30px', textAlign: 'center', borderRadius: 36, background: '#fffaf0ee',
        border: `6px solid ${C.ink}`, opacity: lessonIn, transform: `scale(${0.9 + 0.1 * lessonIn})`, fontFamily: 'Noto Sans Devanagari', color: C.ink}}>
        <div style={{fontSize: 64, fontWeight: 700, color: '#8a3a1e'}}>सीख</div>
        <div style={{fontSize: 62, fontWeight: 700, lineHeight: 1.3}}>सूझबूझ से हर मुश्किल आसान</div>
        <div style={{fontSize: 34, fontFamily: 'DejaVu Sans', marginTop: 12}}>Clever thinking makes hard things easy</div>
      </div>
    </AbsoluteFill>
  );
};
