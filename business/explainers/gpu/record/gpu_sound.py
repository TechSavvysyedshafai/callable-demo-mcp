"""Synthetic GPU hum and coil whine generated in code from the recorded utilisation and clock.

Layers (all follow the gauges):
- Coil whine: a thin high tone whose pitch tracks the clock (about 6 kHz at 1.4 GHz up to 9.5 kHz at 2.5 GHz),
  louder with utilisation, with a fast flutter like real load-dependent whine.
- Fan: filtered noise plus a blade tone; fan speed (pitch and level) follows power draw with lag.
- Electrical hum: 100 Hz mains hum and harmonics (India, 50 Hz mains), always faint.
Usage: python3 gpu_sound.py rec.json out.wav
"""
import json, sys, wave
import numpy as np

src, out = sys.argv[1], sys.argv[2]
log = json.load(open(src)); fps = log['fps']; fr = log['frames']
SR = 48000; n = int(len(fr) / fps * SR)
tf = np.arange(len(fr)) / fps; t = np.arange(n) / SR
util = np.interp(t, tf, [f['util'] for f in fr])
clock = np.interp(t, tf, [f['clock'] for f in fr])
power = np.interp(t, tf, [f['power'] for f in fr])
rng = np.random.default_rng(3)

# coil whine
f_w = 6000 + (clock - 1400) / 1100 * 3500
ph = np.cumsum(f_w) / SR
flutter = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * np.cumsum(30 + 90 * util) / SR))   # load bursts
whine = (np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph)) * flutter * (0.02 + 0.10 * util ** 1.5)

# fan (follows power with lag)
fan = np.copy(power); a = 1 / (SR * 1.5)
for i in range(1, n): fan[i] = fan[i-1] + (power[i] - fan[i-1]) * a
fan_n = (fan - 70) / 380
noise = rng.standard_normal(n)
k = 24; air = np.convolve(noise, np.ones(k) / k, mode='same')
blade = np.sin(2 * np.pi * np.cumsum(180 + 520 * fan_n) / SR)
fan_sig = (air * 1.6 + 0.25 * blade) * (0.05 + 0.35 * fan_n)

# mains hum
hum = 0.04 * (np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t) + 0.25 * np.sin(2 * np.pi * 300 * t))

sig = whine + fan_sig + hum
fade = int(0.3 * SR); sig[:fade] *= np.linspace(0, 1, fade); sig[-fade:] *= np.linspace(1, 0, fade)
sig /= np.max(np.abs(sig)) / 0.8
w = wave.open(out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((sig * 32767).astype('<i2').tobytes()); w.close()
print(f'wrote {out}: whine {f_w.min():.0f}-{f_w.max():.0f} Hz, util {util.min():.2f}-{util.max():.2f}')
