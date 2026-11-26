// Pure (no DOM) versions of two drawing helpers from JDhruv14/line-art-animation lib/ink.ts (MIT, see LICENSE),
// so they can be used inside Remotion's React rendering. Same maths: limb() -> limbPaths(), shoe() -> shoePath().
import type { Pt, Vec } from './ink.ts';
import { pt } from './ink.ts';

/** A limb as two open pen lines either side of a soft curve through the joints, with a paper fill between. */
export function limbPaths(joints: readonly Pt[], width: number, w = 1.35, endGap: readonly [number, number] = [0.4, 0.9]): {fill: string; a: string; b: string} {
  const half = (width - w) / 2;
  const s = joints[0], e = joints[joints.length - 1];
  let c: Vec = [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
  if (joints.length === 3) { const m = joints[1]; c = [m[0] + 0.55 * (m[0] - c[0]), m[1] + 0.55 * (m[1] - c[1])]; }
  const P: Vec[] = [];
  for (let i = 0; i <= 16; i++) { const t = i / 16, u = 1 - t; P.push([u * u * s[0] + 2 * u * t * c[0] + t * t * e[0], u * u * s[1] + 2 * u * t * c[1] + t * t * e[1]]); }
  const side = (sgn: number): Vec[] => P.map((p, i) => {
    const q = P[Math.min(P.length - 1, i + 1)], o = P[Math.max(0, i - 1)];
    const dx = q[0] - o[0], dy = q[1] - o[1], l = Math.hypot(dx, dy) || 1;
    return [p[0] - (dy / l) * half * sgn, p[1] + (dx / l) * half * sgn];
  });
  const L = side(1), R = side(-1);
  const cut = (arr: Vec[], gap: number) => arr.slice(0, arr.length - Math.round(gap * 2));
  return { fill: 'M' + L.map(pt).join('L') + 'L' + R.slice().reverse().map(pt).join('L') + 'Z',
           a: 'M' + cut(L, endGap[0]).map(pt).join('L'), b: 'M' + cut(R, endGap[1]).map(pt).join('L') };
}

/** Shoe or bare foot: a fat ink wedge at the ankle, pitched by `toe` degrees. */
export function shoePath(ankle: Pt, toe = 0): string {
  const r = (toe * Math.PI) / 180, c = Math.cos(r), s = Math.sin(r);
  const S = (x: number, y: number): Vec => [ankle[0] + x * c - y * s, ankle[1] + x * s + y * c];
  return `M${pt(S(-1.6, -0.6))} L${pt(S(4.6, -0.2))} Q${pt(S(6.6, 0.4))} ${pt(S(5.6, 1.6))} L${pt(S(-1.4, 1.5))} Q${pt(S(-2.2, 0.5))} ${pt(S(-1.6, -0.6))}Z`;
}
