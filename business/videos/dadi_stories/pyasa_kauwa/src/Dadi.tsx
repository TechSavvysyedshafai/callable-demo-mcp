// Dadi, the storyteller: an ink line-art figure. Walk solved by gait.ts and limbs drawn in the open-stroke style of
// JDhruv14/line-art-animation (MIT). Everything is computed from the time t, so every frame is the same on every render.
import React from 'react';
import {gait} from './lineart/gait';
import {joint, hang, pt} from './lineart/ink';
import {limbPaths, shoePath} from './lineart/pure';

const INK = '#2a1d14', PAPER = '#fdf8ee', SARI = '#e0892f', BORDER = '#8a2a1e', SKIN = '#f3d9b8';
const walk = gait({kind: 'shuffle', period: 1.0, stride: 16});
const PEN = 1.35;
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
const ease = (x: number) => { const t = clamp(x, 0, 1); return t * t * (3 - 2 * t); };

const Limb: React.FC<{j: number[][]; w: number; fill?: string}> = ({j, w, fill = SKIN}) => {
  const p = limbPaths(j, w, PEN);
  return (<g><path d={p.fill} fill={fill} /><path d={p.a} fill="none" stroke={INK} strokeWidth={PEN} strokeLinecap="round" /><path d={p.b} fill="none" stroke={INK} strokeWidth={PEN} strokeLinecap="round" /></g>);
};

/** x0 -> x1 walk between t0 and t1, then stand. Gestures: fan (hot day), raise (the lesson). */
export const Dadi: React.FC<{t: number; scale: number; ground: number; x0: number; x1: number; t0: number; t1: number; fan: [number, number]; raise: [number, number]}> =
({t, scale, ground, x0, x1, t0, t1, fan, raise}) => {
  // travel: constant speed from the gait so the planted foot does not slide
  const speed = walk.speed*scale;                                     // scene px per second
  const dist = Math.min(Math.max(0, t - t0)*speed, x1 - x0);
  const x = x0 + dist;
  const moving = t > t0 && dist < x1 - x0;
  const go = moving ? 1 : 1 - ease((t - (t0 + (x1 - x0)/speed))/0.35);
  const phase = dist/(walk.speed*scale)/walk.period;
  const p = walk.pose(phase, clamp(go, 0, 1));
  const breathe = Math.sin(t*2.1)*0.5;
  const hip = p.hip, waistY = hip[1] - 2, shY = hip[1] - 29 + breathe, stoop = 5;
  const sh: number[] = [40 + stoop, shY], head: number[] = [40 + stoop + 4, shY - 12];
  // far arm: swings while walking, fans the face on the hot day, rises for the lesson
  const fanK = ease((t - fan[0])/0.4)*(1 - ease((t - fan[1])/0.4)), raiseK = ease((t - raise[0])/0.5)*(1 - ease((t - raise[1])/0.5));
  const swing = 16*Math.cos(2*Math.PI*phase)*clamp(go, 0, 1);
  let hand = hang(sh, 22, -swing);
  const fanHand = [head[0] + 14, head[1] + 6 + 1.5*Math.sin(t*14)], upHand = [head[0] + 12, head[1] - 16 + 1.5*Math.sin(t*5)];
  hand = [hand[0] + (fanHand[0] - hand[0])*fanK + (upHand[0] - hand[0])*raiseK, hand[1] + (fanHand[1] - hand[1])*fanK + (upHand[1] - hand[1])*raiseK] as [number, number];
  const elbow = joint(sh, hand, 11.5, 11.5, -1);
  // near arm holds the walking stick; the stick tip plants ahead of the front foot
  const front = p.feet[p.front].ankle;
  const sHand: number[] = [sh[0] + 11, sh[1] + 19 + Math.sin(2*Math.PI*phase*2)*0.8*go];
  const sElbow = joint([sh[0] + 1, sh[1] + 1], sHand, 11, 11, -1);
  const tip: number[] = [Math.max(front[0] + 5, sHand[0] + 2), 120];
  // sari: from the waist to just above the ankles, widening with the stride
  const ax = p.feet.map(f => f.ankle[0]), lo = Math.min(...ax) - 6, hi = Math.max(...ax) + 7;
  const sari = `M${pt([34, waistY])} L${pt([lo, 117])} Q${pt([(lo + hi)/2, 119.5])} ${pt([hi, 117])} L${pt([49, waistY])} Z`;
  const torso = `M${pt([34, waistY])} Q${pt([31, shY + 12])} ${pt([sh[0] - 6, shY + 1])} Q${pt([sh[0], shY - 2])} ${pt([sh[0] + 6, shY + 2])} Q${pt([52, shY + 14])} ${pt([49, waistY])} Z`;
  const pallu = `M${pt([sh[0] + 5, shY + 1])} L${pt([sh[0] - 3, shY - 1])} Q${pt([28 + Math.sin(t*1.7)*1.2, shY + 16])} ${pt([27 + Math.sin(t*1.7)*2, waistY + 10])} L${pt([33, waistY + 6])} L${pt([46, shY + 10])} Z`;
  const gx = (scale: number) => scale;
  return (
    <g transform={`translate(${x} ${ground}) scale(${gx(scale)}) translate(-40 -120)`} strokeLinejoin="round">
      {/* far arm behind the body */}
      <Limb j={[sh, elbow, hand]} w={4.2} />
      <circle cx={hand[0]} cy={hand[1]} r={2} fill={SKIN} stroke={INK} strokeWidth={PEN} />
      {/* feet below the sari */}
      {p.feet.map((f, i) => <path key={i} d={shoePath(f.ankle, f.pitch)} fill={INK} />)}
      <path d={sari} fill={SARI} stroke={INK} strokeWidth={PEN} />
      <path d={`M${pt([lo + 0.6, 115.2])} Q${pt([(lo + hi)/2, 117.6])} ${pt([hi - 0.6, 115.2])}`} fill="none" stroke={BORDER} strokeWidth={2.4} />
      <path d={torso} fill={BORDER} stroke={INK} strokeWidth={PEN} />
      <path d={pallu} fill={SARI} stroke={INK} strokeWidth={PEN} />
      {/* neck and head */}
      <path d={`M${pt([head[0] - 2, head[1] + 6])} L${pt([head[0] - 2.5, shY])} M${pt([head[0] + 2, head[1] + 6])} L${pt([head[0] + 1.5, shY])}`} stroke={INK} strokeWidth={PEN} />
      <circle cx={head[0] - 7} cy={head[1] - 3} r={3.6} fill="#e9e6df" stroke={INK} strokeWidth={PEN} />
      <circle cx={head[0]} cy={head[1]} r={7.4} fill={SKIN} stroke={INK} strokeWidth={PEN} />
      <path d={`M${pt([head[0] - 7.3, head[1] - 0.5])} Q${pt([head[0] - 4, head[1] - 9.5])} ${pt([head[0] + 5.5, head[1] - 5])} Q${pt([head[0] - 1, head[1] - 4])} ${pt([head[0] - 6.8, head[1] + 2.5])} Z`} fill="#e9e6df" stroke={INK} strokeWidth={PEN*0.8} />
      <circle cx={head[0] + 3.4} cy={head[1] - 0.6} r={2.1} fill="none" stroke={INK} strokeWidth={PEN*0.7} />
      <circle cx={head[0] + 3.6} cy={head[1] - 0.5} r={0.7} fill={INK} />
      <circle cx={head[0] + 5.6} cy={head[1] - 4.2} r={0.75} fill="#d3302a" />
      <path d={`M${pt([head[0] + 2.4, head[1] + 3.4])} Q${pt([head[0] + 4.4, head[1] + 4.8])} ${pt([head[0] + 6, head[1] + 3])}`} fill="none" stroke={INK} strokeWidth={PEN*0.7} strokeLinecap="round" />
      {/* near arm and the stick in front */}
      <path d={`M${pt(sHand)} L${pt(tip)}`} stroke="#6b4423" strokeWidth={2.2} strokeLinecap="round" />
      <Limb j={[[sh[0] + 1, sh[1] + 1], sElbow, sHand]} w={4.2} />
      <circle cx={sHand[0]} cy={sHand[1]} r={2} fill={SKIN} stroke={INK} strokeWidth={PEN} />
      {fanK > 0.3 && (() => { const ang = 25*Math.sin(t*14); return (
        <g transform={`translate(${hand[0]} ${hand[1]}) rotate(${30 + ang})`}>
          <path d="M0 0 L0 -6" stroke="#6b4423" strokeWidth={1.2} strokeLinecap="round" />
          <path d="M-4.5 -6 Q0 -8 4.5 -6 L4 -13 Q0 -15 -4 -13 Z" fill="#c9a24a" stroke={INK} strokeWidth={PEN*0.8} />
          <path d="M-3 -8 L3 -8 M-3 -10.5 L3 -10.5" stroke="#8d6a20" strokeWidth={0.6} />
        </g>); })()}
      {raiseK > 0.5 && <path d={`M${pt([hand[0], hand[1] - 1.5])} L${pt([hand[0] + 0.5, hand[1] - 5.5])}`} stroke={INK} strokeWidth={1.6} strokeLinecap="round" />}
    </g>
  );
};
