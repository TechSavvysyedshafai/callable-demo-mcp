// 20-second vertical sample ad for a coaching centre. Footage in the middle is our own 3D explainers.
// Centre name, address and phone are placeholders to replace with the real centre's details.
import React from 'react';
import {AbsoluteFill, Easing, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

const C = {navy: '#0f1f3d', navy2: '#18305e', saffron: '#ff9f1c', cream: '#fff6e5', white: '#ffffff', red: '#e4572e', mint: '#7bdcb5'};
const HI = '"Noto Sans Devanagari", "DejaVu Sans", sans-serif', EN = '"DejaVu Sans", sans-serif';
const k = (t: number, a: number[], b: number[]) => interpolate(t, a, b, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
const FORMULAS = ['E = mc²', 'PV = nRT', 'x²/a² + y²/b² = 1', 'F = ma', 'N₂ + 3H₂ ⇌ 2NH₃', 'v = u + at', 'sin²θ + cos²θ = 1', 'pH = −log[H⁺]'];

const Background: React.FC<{t: number}> = ({t}) => (
  <AbsoluteFill style={{background: `radial-gradient(circle at 50% 35%, ${C.navy2}, ${C.navy} 70%)`}}>
    {FORMULAS.map((f, i) => {
      const y = ((i * 260 + t * 40) % 2100) - 120, x = (i * 397) % 900 + 40;
      return <div key={i} style={{position: 'absolute', left: x, top: 1920 - y, fontFamily: EN, fontSize: 34, color: C.white, opacity: 0.09, transform: `rotate(${(i % 3 - 1) * 6}deg)`}}>{f}</div>;
    })}
  </AbsoluteFill>
);

const Hook: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig(), t = f / fps;
  const words = ['Physics', 'Chemistry', 'Maths'];
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 18}}>
      {words.map((w, i) => {
        const s = spring({frame: f - i * 7, fps, config: {damping: 12}});
        return <div key={w} style={{fontFamily: EN, fontWeight: 700, fontSize: 120, color: [C.saffron, C.mint, C.white][i], transform: `translateX(${(1 - s) * (i % 2 ? 600 : -600)}px) rotate(${(1 - s) * 8}deg)`}}>{w}</div>;
      })}
      <div style={{fontFamily: HI, fontWeight: 700, fontSize: 96, color: C.white, marginTop: 40, opacity: k(t, [1.1, 1.5], [0, 1]), transform: `scale(${k(t, [1.1, 1.6], [0.7, 1])})`}}>समझ नहीं आता?</div>
    </AbsoluteFill>
  );
};

const Show: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig(), t = f / fps;
  const first = t < 3;
  const s = spring({frame: f, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{alignItems: 'center', flexDirection: 'column'}}>
      <div style={{marginTop: 250, fontFamily: HI, fontWeight: 700, fontSize: 88, color: C.white, textAlign: 'center', lineHeight: 1.25, transform: `translateY(${(1 - s) * -80}px)`, opacity: s}}>
        अब <span style={{color: C.saffron}}>3D</span> में देखो,<br />समझो
      </div>
      <div style={{marginTop: 70, width: 960, borderRadius: 40, background: '#0a0f1a', padding: 26, boxShadow: '0 30px 80px rgba(0,0,0,0.5)', transform: `scale(${0.85 + 0.15 * s}) rotate(${(1 - s) * -4}deg)`}}>
        <div style={{borderRadius: 18, overflow: 'hidden', height: 520, background: '#fbfaf6'}}>
          {first ? <OffthreadVideo src={staticFile('clip_conics.mp4')} style={{width: '100%'}} muted />
                 : <Sequence from={90}><OffthreadVideo src={staticFile('clip_chem.mp4')} style={{width: '100%'}} muted /></Sequence>}
        </div>
      </div>
      <div style={{marginTop: 46, fontFamily: EN, fontSize: 52, color: C.mint, fontWeight: 700}}>{first ? 'Conic Sections · Maths' : 'Chemical Equilibrium · Chemistry'}</div>
      <div style={{marginTop: 10, fontFamily: HI, fontSize: 44, color: C.cream, opacity: 0.85}}>{first ? 'cone काटो, curves बनते देखो' : 'दबाओ, गरम करो, reaction बदलते देखो'}</div>
    </AbsoluteFill>
  );
};

const Features: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig();
  const items = [['Class 11–12 · JEE · NEET', 'पूरा syllabus'], ['3D animated classes', 'हर chapter को देखकर समझो'], ['Daily doubt sessions', 'रोज़ सवाल पूछो']];
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 40}}>
      {items.map(([a, b], i) => {
        const s = spring({frame: f - i * 12, fps, config: {damping: 13}});
        return (
          <div key={a} style={{width: 900, padding: '38px 44px', borderRadius: 32, background: C.cream, display: 'flex', alignItems: 'center', gap: 34, transform: `translateX(${(1 - s) * 1100}px) translateY(${Math.sin(f / fps * 2.2 + i) * 10}px) rotate(${Math.sin(f / fps * 1.6 + i * 2) * 0.8}deg)`, boxShadow: '0 16px 40px rgba(0,0,0,0.35)'}}>
            <div style={{width: 92, height: 92, borderRadius: 46, background: [C.saffron, C.mint, C.red][i], color: C.navy, fontFamily: EN, fontWeight: 700, fontSize: 52, display: 'grid', placeItems: 'center', transform: `scale(${1 + 0.08 * Math.sin(f / fps * 5 + i)})`}}>✓</div>
            <div><div style={{fontFamily: EN, fontWeight: 700, fontSize: 54, color: C.navy}}>{a}</div><div style={{fontFamily: HI, fontSize: 40, color: '#4a5a78', marginTop: 6}}>{b}</div></div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Offer: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig(), t = f / fps;
  const s = spring({frame: f, fps, config: {damping: 9}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column'}}>
      <svg width={900} height={900} style={{position: 'absolute', transform: `rotate(${t * 20}deg) scale(${s})`}} viewBox="-450 -450 900 900">
        {Array.from({length: 18}).map((_, i) => <path key={i} d="M0 0 L-60 -440 L60 -440 Z" fill={C.saffron} opacity={0.22} transform={`rotate(${i * 20})`} />)}
      </svg>
      <div style={{fontFamily: EN, fontWeight: 800, fontSize: 150, color: C.saffron, transform: `scale(${s})`, textShadow: '0 8px 0 rgba(0,0,0,0.3)'}}>FREE</div>
      <div style={{fontFamily: HI, fontWeight: 700, fontSize: 104, color: C.white, transform: `scale(${s})`}}>डेमो क्लास</div>
      <div style={{marginTop: 50, padding: '18px 40px', borderRadius: 60, background: C.red, fontFamily: EN, fontWeight: 700, fontSize: 52, color: C.white, opacity: k(t, [0.6, 1.0], [0, 1])}}>Admission open · 2027</div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 26, opacity: s}}>
      <div style={{width: 200, height: 200, borderRadius: 100, border: `8px solid ${C.saffron}`, display: 'grid', placeItems: 'center', fontFamily: EN, fontSize: 40, color: C.saffron, fontWeight: 700}}>LOGO</div>
      <div style={{fontFamily: EN, fontWeight: 800, fontSize: 80, color: C.white, textAlign: 'center'}}>[Your Centre Name]</div>
      <div style={{fontFamily: EN, fontSize: 48, color: C.cream}}>[Address], Patna</div>
      <div style={{marginTop: 20, padding: '24px 48px', borderRadius: 24, background: C.mint, fontFamily: EN, fontWeight: 700, fontSize: 58, color: C.navy}}>Call / WhatsApp: [Number]</div>
      <div style={{position: 'absolute', bottom: 60, fontFamily: EN, fontSize: 28, color: C.white, opacity: 0.45}}>Sample ad · details to be replaced</div>
    </AbsoluteFill>
  );
};

export const Ad: React.FC = () => {
  const f = useCurrentFrame(), {fps} = useVideoConfig(), t = f / fps;
  return (
    <AbsoluteFill>
      <Background t={t} />
      <Sequence durationInFrames={3 * fps}><Hook /></Sequence>
      <Sequence from={3 * fps} durationInFrames={6 * fps}><Show /></Sequence>
      <Sequence from={9 * fps} durationInFrames={5 * fps}><Features /></Sequence>
      <Sequence from={14 * fps} durationInFrames={3 * fps}><Offer /></Sequence>
      <Sequence from={17 * fps}><EndCard /></Sequence>
    </AbsoluteFill>
  );
};
