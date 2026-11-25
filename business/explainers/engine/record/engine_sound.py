"""Engine sound generated in code from the recorded rpm, so the pitch follows the tachometer.

An inline-4 fires twice per crank revolution, so the firing frequency is rpm / 60 * 2.
Each firing is a short decaying pulse; a phase accumulator keeps the pulses in step as rpm changes.
Layers: firing pulses (the 'note'), a sub rumble at half the firing rate, throttle-dependent intake
noise, and a mild soft-clip for grit. Usage: python3 engine_sound.py rpm.json out.wav
"""
import json, sys, wave
import numpy as np

src, out = sys.argv[1], sys.argv[2]
log = json.load(open(src)); fps = log['fps']; fr = log['frames']
SR = 48000
dur = len(fr) / fps
n = int(dur * SR)
t_frames = np.arange(len(fr)) / fps
t = np.arange(n) / SR
rpm = np.interp(t, t_frames, [f['rpm'] for f in fr])
thr = np.interp(t, t_frames, [f['thr'] for f in fr])

f_fire = rpm / 60.0 * 2.0                      # firing pulses per second
phase = np.cumsum(f_fire) / SR                 # cycles of the firing pulse
frac = phase - np.floor(phase)
# each firing: a sharp attack and an exponential decay, brighter with throttle
pulse = np.exp(-frac * (9 + 10 * (1 - thr))) * (1 - np.exp(-frac * 200))
body = np.zeros(n)
for h, a in [(1, 1.0), (2, 0.55), (3, 0.35), (4, 0.22), (6, 0.12)]:
    body += a * np.sin(2 * np.pi * h * phase) * pulse
rumble = 0.35 * np.sin(np.pi * phase) * (0.6 + 0.4 * pulse)   # half firing rate
rng = np.random.default_rng(7)
noise = rng.standard_normal(n)
k = 60; noise = np.convolve(noise, np.ones(k) / k, mode='same')  # crude low-pass
intake = noise * (0.15 + 1.4 * thr) * (0.5 + 0.5 * pulse)
sig = body + rumble + intake
sig = np.tanh(1.6 * sig)                       # soft clip for grit
level = 0.25 + 0.75 * np.clip((rpm - 700) / 6000, 0, 1) ** 0.6
sig *= level
fade = int(0.3 * SR); sig[:fade] *= np.linspace(0, 1, fade); sig[-fade:] *= np.linspace(1, 0, fade)
sig /= np.max(np.abs(sig)) / 0.85
w = wave.open(out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((sig * 32767).astype('<i2').tobytes()); w.close()
print(f'wrote {out}: {dur:.1f}s, rpm {rpm.min():.0f}-{rpm.max():.0f}, firing {f_fire.min():.0f}-{f_fire.max():.0f} Hz')
