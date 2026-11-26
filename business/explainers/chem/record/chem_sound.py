"""Sound made in code from the recorded simulation log (rpm.json): every layer follows what is on screen.
- Gas hiss: noise whose loudness follows pressure and whose brightness follows temperature (faster molecules).
- Reaction pings: a soft high ping for every ammonia made (heat out), a lower ping for every ammonia split.
- Piston thud: low rumble while the piston moves.
- Heater hum: a mains-like hum that grows with temperature.
Usage: python3 chem_sound.py rpm.json out.wav
"""
import json, sys, wave
import numpy as np

src, out = sys.argv[1], sys.argv[2]
log = json.load(open(src)); fps = log['fps']; fr = log['frames']
SR = 48000; n = int(len(fr) / fps * SR); t = np.arange(n) / SR; tf = np.arange(len(fr)) / fps
P = np.interp(t, tf, [f['P'] for f in fr]); T = np.interp(t, tf, [f['tc'] for f in fr]); V = np.interp(t, tf, [f['V'] for f in fr])
rng = np.random.default_rng(5)

def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))

w = rng.standard_normal(n)
dark, bright = band(w, 200, 1500), band(w, 1500, 7000)
heat = np.clip((T - 300) / 300, 0, 1)
hiss = (dark * (1 - 0.6 * heat) + bright * (0.3 + 0.7 * heat)) * (0.02 + 0.08 * np.clip(P / 400, 0, 1.3))

pings = np.zeros(n); k = np.arange(int(0.09 * SR)) / SR
up = np.sin(2 * np.pi * 1320 * k) * np.exp(-k * 45); down = np.sin(2 * np.pi * 620 * k) * np.exp(-k * 35)
for i, f in enumerate(fr):
    for kind, cnt, shape, amp in (('fe', f['fe'], up, 0.10), ('re', f['re'], down, 0.09)):
        for _ in range(min(cnt, 4)):
            a = int((i + rng.random()) / fps * SR)
            if a + len(shape) < n: pings[a:a + len(shape)] += shape * amp

dV = np.abs(np.gradient(V)) * SR
thud = band(rng.standard_normal(n), 30, 180) * np.clip(dV / 0.5, 0, 1) * 1.5
hum = (np.sin(2 * np.pi * 100 * t) + 0.4 * np.sin(2 * np.pi * 200 * t)) * 0.03 * heat

sig = hiss + pings + thud + hum
fade = int(0.3 * SR); sig[:fade] *= np.linspace(0, 1, fade); sig[-fade:] *= np.linspace(1, 0, fade)
sig /= np.max(np.abs(sig)) / 0.85
wv = wave.open(out, 'wb'); wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes((sig * 32767).astype('<i2').tobytes()); wv.close()
print(f'wrote {out}: {sum(f["fe"] for f in fr)} NH3 made, {sum(f["re"] for f in fr)} split, P {P.min():.0f}-{P.max():.0f} atm')
