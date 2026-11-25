"""Sound made in code: a soft music bed and short sound effects. No downloads, no licences needed.

music_bed(seconds, kind)  -> float32 array at SR, a slow four-chord pad (kinds: warm, minimal, none)
sfx(name)                 -> float32 array, one of: whoosh, pop, tick, rumble, rise
"""
import numpy as np

SR = 48000
CHORDS = {  # root-position triads in Hz, Am  F  C  G
    'warm': [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (261.6, 329.6, 392.0), (196.0, 246.9, 293.7)],
}


def music_bed(seconds, kind='warm', bar=4.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    if kind == 'none':
        return np.zeros(n, np.float32)
    out = np.zeros(n)
    chords = CHORDS['warm']
    for i in range(int(np.ceil(seconds / bar)) + 1):
        a, b = int(i * bar * SR), min(n, int((i + 1) * bar * SR + 0.5 * SR))
        if a >= n:
            break
        seg = t[a:b] - i * bar
        env = np.minimum(1, seg / 1.2) * np.minimum(1, np.maximum(0, (bar + 0.5 - seg) / 1.0))
        for f in chords[i % 4]:
            tone = np.sin(2 * np.pi * f * seg) + 0.3 * np.sin(2 * np.pi * 2 * f * seg) + 0.1 * np.sin(2 * np.pi * 3 * f * seg)
            out[a:b] += 0.06 * env * tone
        if kind == 'warm':  # soft low root note on each beat
            root = chords[i % 4][0] / 2
            for k in range(4):
                s = seg - k * bar / 4
                m = s >= 0
                out[a:b][m] += 0.05 * np.sin(2 * np.pi * root * s[m]) * np.exp(-s[m] * 3)
    fade = int(1.5 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def _smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')


def sfx(name):
    if name == 'whoosh':
        n = int(0.7 * SR); s = np.linspace(0, 1, n)
        x = _smooth(_noise(n, 1), 6) - _smooth(_noise(n, 1), 60)
        return (x * np.sin(np.pi * s) ** 2 * 0.6).astype(np.float32)
    if name == 'pop':
        n = int(0.15 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * (600 - 2000 * t) * t) * np.exp(-t * 35) * 0.5).astype(np.float32)
    if name == 'tick':
        n = int(0.05 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 120) * 0.4).astype(np.float32)
    if name == 'rumble':
        n = int(1.2 * SR); s = np.linspace(0, 1, n)
        return (_smooth(_noise(n, 3), 300) * 12 * np.sin(np.pi * s) * 0.5).astype(np.float32)
    if name == 'rise':
        n = int(1.0 * SR); t = np.arange(n) / SR
        ph = np.cumsum(300 + 900 * (t / t[-1]) ** 2) / SR
        return (np.sin(2 * np.pi * ph) * (t / t[-1]) * np.exp(-((t - t[-1]) ** 2) * 0) * 0.25).astype(np.float32)
    raise ValueError(f'unknown sound effect {name!r} (use whoosh, pop, tick, rumble, rise)')
