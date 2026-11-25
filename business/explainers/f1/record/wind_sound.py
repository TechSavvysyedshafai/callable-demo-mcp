"""Synthetic wind rush and vortex sound generated in code from the recorded airspeed and DRS state.

Layers (all follow the gauges):
- Wind rush: band-passed noise; its centre frequency rises with airspeed (about 300 Hz at 80 km/h up to
  2.6 kHz at 340 km/h) and its loudness grows with speed squared, like dynamic pressure.
- Vortex whistle: a faint tone that wavers, pitched by airspeed; louder with DRS closed (stronger rear-wing tip vortices).
- Buffet rumble: low noise from the turbulent wake; DRS open cuts it and lifts the rush slightly.
- DRS whoosh: a short swell each time the flap opens or closes.
Usage: python3 wind_sound.py rec.json out.wav
"""
import json, sys, wave
import numpy as np

src, out = sys.argv[1], sys.argv[2]
log = json.load(open(src)); fps = log['fps']; fr = log['frames']
SR = 48000; n = int(len(fr) / fps * SR)
tf = np.arange(len(fr)) / fps; t = np.arange(n) / SR
v = np.interp(t, tf, [f['v'] for f in fr])                 # km/h
flap = np.interp(t, tf, [f['flap'] for f in fr])           # 0 closed .. 1 open
rng = np.random.default_rng(11)
vn = np.clip((v - 80) / 260, 0, 1)
q = (v / 340.0) ** 2                                        # dynamic pressure, normalised

def bandpass(x, fc, q_=1.2):
    """Time-varying state-variable band-pass filter."""
    y = np.zeros_like(x); low = band = 0.0
    for i in range(len(x)):
        f = 2 * np.sin(np.pi * min(fc[i], SR / 6) / SR)
        high = x[i] - low - band / q_
        band += f * high; low += f * band
        y[i] = band
    return y

noise = rng.standard_normal(n)
fc = 300 + vn * 2300 + flap * 250
rush = bandpass(noise, fc) * (0.15 + 0.85 * q)
# vortex whistle: wavering tone, stronger when DRS is closed
f_wh = 420 + vn * 900
ph = np.cumsum(f_wh * (1 + 0.01 * np.sin(2 * np.pi * 5.3 * t))) / SR
whistle = np.sin(2 * np.pi * ph) * (0.03 + 0.10 * q) * (1 - 0.6 * flap)
# buffet rumble from the wake
k = 220; rumble = np.convolve(rng.standard_normal(n), np.ones(k) / k, mode='same') * 6
rumble *= (0.1 + 0.5 * q) * (1 - 0.5 * flap)
# whoosh when the flap moves
dflap = np.abs(np.gradient(flap)) * SR
whoosh = bandpass(rng.standard_normal(n), 900 + 1500 * flap) * np.clip(dflap / 8, 0, 1) * 1.2

sig = rush + whistle + rumble + whoosh
fade = int(0.3 * SR); sig[:fade] *= np.linspace(0, 1, fade); sig[-fade:] *= np.linspace(1, 0, fade)
sig /= np.max(np.abs(sig)) / 0.85
w = wave.open(out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((sig * 32767).astype('<i2').tobytes()); w.close()
print(f'wrote {out}: airspeed {v.min():.0f}-{v.max():.0f} km/h, rush centre {fc.min():.0f}-{fc.max():.0f} Hz')
