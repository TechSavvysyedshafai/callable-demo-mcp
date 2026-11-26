"""Sound made in code from the recorded log (rpm.json); every layer follows the screen.
- A soft pad whose pitch follows eccentricity (circle low, hyperbola high): pitch = 196 Hz x 2^e.
- A chime each time the curve changes type (circle, ellipse, parabola, hyperbola), higher for higher e.
- A whoosh while the plane tilts or moves.
- A low bell when the Dandelin spheres appear.
Usage: python3 conic_sound.py rpm.json out.wav
"""
import json, sys, wave
import numpy as np

src, out = sys.argv[1], sys.argv[2]
log = json.load(open(src)); fps = log['fps']; fr = log['frames']
SR = 48000; n = int(len(fr) / fps * SR); t = np.arange(n) / SR; tf = np.arange(len(fr)) / fps
e = np.interp(t, tf, [f['e'] for f in fr]); beta = np.interp(t, tf, [f['beta'] for f in fr]); d = np.interp(t, tf, [f['d'] for f in fr])
f0 = 196 * 2 ** e
ph = np.cumsum(f0) / SR
pad = (np.sin(2*np.pi*ph) + 0.5*np.sin(2*np.pi*1.5*ph) + 0.3*np.sin(2*np.pi*2*ph)) * 0.05 * (1 + 0.15*np.sin(2*np.pi*0.3*t))

def chime(freq, dur=1.6, amp=0.22):
    k = np.arange(int(dur*SR)) / SR
    return (np.sin(2*np.pi*freq*k) + 0.4*np.sin(2*np.pi*2.76*freq*k)) * np.exp(-k*3.2) * amp

sig = pad.copy()
prev = fr[0]['type']; sph = fr[0]['spheres']
for i, f in enumerate(fr):
    a = int(i / fps * SR)
    if f['type'] != prev:
        c = chime(523 * 2 ** (f['e'] / 2)); sig[a:a+len(c)] += c[:n-a]; prev = f['type']
    if f['spheres'] and not sph:
        c = chime(262, 2.5, 0.25); sig[a:a+len(c)] += c[:n-a]
    sph = f['spheres']
motion = np.abs(np.gradient(beta)) * SR * 3 + np.abs(np.gradient(d)) * SR * 0.6
noise = np.random.default_rng(3).standard_normal(n)
X = np.fft.rfft(noise); fq = np.fft.rfftfreq(n, 1/SR); X[(fq < 400) | (fq > 3000)] = 0; noise = np.fft.irfft(X, n)
sig += noise * np.clip(motion, 0, 1) * 0.12
fade = int(0.3*SR); sig[:fade] *= np.linspace(0, 1, fade); sig[-fade:] *= np.linspace(1, 0, fade)
sig /= np.max(np.abs(sig)) / 0.85
w = wave.open(out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((sig*32767).astype('<i2').tobytes()); w.close()
print(f'wrote {out}: e {e.min():.2f}-{e.max():.2f}, {sum(1 for a, b in zip(fr, fr[1:]) if a["type"] != b["type"])} curve changes')
