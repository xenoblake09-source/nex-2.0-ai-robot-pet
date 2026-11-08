#!/usr/bin/env python3
"""
Generate NEX's animal voice assets.

Every sound is synthesised from scratch with numpy (formant-ish tone stacks,
noise bursts, envelopes) — they are original recordings, so there are no
licensing restrictions and the whole set is tiny.

    python3 tools/generate_animal_sounds.py

Output: app/public/sounds/<animal>.wav  (22050 Hz, mono, 16-bit PCM)
        app/public/sounds/start.wav, error.wav, chime.wav
"""
from __future__ import annotations

import os
import sys

import numpy as np

SR = 22050
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "public", "sounds"
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def t_axis(duration: float) -> np.ndarray:
    return np.linspace(0, duration, int(SR * duration), endpoint=False)


def env_ar(n: int, attack: float, release: float, curve: float = 1.0) -> np.ndarray:
    """Attack/release envelope with an optional exponential tail."""
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    e = np.ones(n)
    a = min(a, n)
    e[:a] = np.linspace(0, 1, a) ** curve
    if r < n:
        e[-r:] = np.linspace(1, 0, r) ** curve
    return e


def env_adsr(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    a_n = max(1, int(a * SR))
    d_n = max(1, int(d * SR))
    r_n = max(1, int(r * SR))
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate(
        [
            np.linspace(0, 1, a_n),
            np.linspace(1, s, d_n),
            np.full(s_n, s),
            np.linspace(s, 0, r_n),
        ]
    )
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def noise(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-1, 1, n)


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """Simple one-pole low-pass."""
    a = float(np.exp(-2 * np.pi * cutoff / SR))
    out = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = a * acc + (1 - a) * v
        out[i] = acc
    return out


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def bandpass(x: np.ndarray, low: float, high: float) -> np.ndarray:
    return highpass(lowpass(x, high), low)


def formant(
    n: int,
    freqs: list[float],
    amps: list[float],
    bandwidths: list[float] | None = None,
    seed: int = 3,
) -> np.ndarray:
    """Resonant filter bank applied to white noise."""
    if bandwidths is None:
        bandwidths = [120.0] * len(freqs)
    src = noise(n, seed)
    out = np.zeros(n)
    for f, amp, bw in zip(freqs, amps, bandwidths):
        out += amp * bandpass(src, max(30, f - bw), f + bw)
    return out


def tone(
    n: int,
    f_start: float,
    f_end: float | None = None,
    harmonics: int = 6,
    noise_mix: float = 0.0,
    seed: int = 5,
    vibrato_hz: float = 0.0,
    vibrato_cents: float = 0.0,
) -> np.ndarray:
    """Additive tone with a pitch glide and optional vibrato."""
    t = t_axis(n / SR)
    f_end = f_start if f_end is None else f_end
    phase = 2 * np.pi * np.cumsum(np.linspace(f_start, f_end, n)) / SR
    if vibrato_hz > 0:
        phase += vibrato_cents * np.sin(2 * np.pi * vibrato_hz * t) / 100.0
    out = np.zeros(n)
    for h in range(1, harmonics + 1):
        out += np.sin(phase * h) / h
    out /= max(1e-6, np.sum(1 / np.arange(1, harmonics + 1)))
    if noise_mix > 0:
        out = out * (1 - noise_mix) + noise(n, seed) * noise_mix
    return out


def am(n: int, rate: float, depth: float = 1.0) -> np.ndarray:
    t = t_axis(n / SR)
    return 1.0 - depth * 0.5 * (1 + np.sin(2 * np.pi * rate * t))


def concat(*parts: np.ndarray) -> np.ndarray:
    return np.concatenate([p for p in parts if len(p) > 0])


def silence(duration: float) -> np.ndarray:
    return np.zeros(int(SR * duration))


def normalize(x: np.ndarray, peak: float = 0.86) -> np.ndarray:
    m = float(np.max(np.abs(x))) or 1.0
    return x / m * peak


def soft_clip(x: np.ndarray) -> np.ndarray:
    return np.tanh(x * 1.25) / math_tanh(1.25)


def math_tanh(v: float) -> float:
    return float(np.tanh(v))


def save(name: str, x: np.ndarray) -> None:
    os.makedirs(OUT, exist_ok=True)
    x = normalize(x)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    path = os.path.join(OUT, f"{name}.wav")
    with open(path, "wb") as fh:
        import wave

        with wave.open(fh, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())
    print(f"  {name}.wav  ({len(x) / SR:.2f}s, {os.path.getsize(path) / 1024:.0f} KB)")


# --------------------------------------------------------------------------
# animal voices
# --------------------------------------------------------------------------
def dog() -> np.ndarray:
    def bark() -> np.ndarray:
        n = int(0.16 * SR)
        t = t_axis(n / SR)
        base = tone(n, 420, 190, harmonics=4, noise_mix=0.25)
        rasp = formant(n, [700, 1500, 2600], [1.0, 0.6, 0.3], [260, 320, 420], seed=11)
        body = base * 0.7 + rasp * 0.9
        body *= env_ar(n, 0.006, 0.09, curve=2.2)
        body *= 1 + 0.5 * np.exp(-t * 26)
        return body

    return concat(bark(), silence(0.07), bark(), silence(0.09), bark() * 0.85)


def cat() -> np.ndarray:
    n = int(0.72 * SR)
    t = t_axis(n / SR)
    # pitch contour: up then down = "mee-ow"
    f = 520 + 260 * np.sin(np.pi * np.linspace(0, 1, n)) - 160 * np.linspace(0, 1, n) ** 3
    phase = 2 * np.pi * np.cumsum(f) / SR
    out = np.zeros(n)
    for h, amp in ((1, 1.0), (2, 0.55), (3, 0.3), (4, 0.18), (5, 0.1)):
        out += amp * np.sin(phase * h)
    out /= 2.1
    out += formant(n, [900, 2100], [0.5, 0.25], [300, 400], seed=21) * 0.25
    out *= env_adsr(n, 0.07, 0.1, 0.75, 0.24)
    out *= 1 + 0.06 * np.sin(2 * np.pi * 5.5 * t)
    return out


def cow() -> np.ndarray:
    n = int(1.25 * SR)
    t = t_axis(n / SR)
    base = tone(n, 132, 118, harmonics=7, vibrato_hz=5.2, vibrato_cents=40)
    base += formant(n, [620, 1150], [0.42, 0.2], [220, 300], seed=31) * 0.4
    base *= env_adsr(n, 0.16, 0.2, 0.85, 0.35)
    base *= 1 + 0.05 * np.sin(2 * np.pi * 5.2 * t)
    return base


def lion() -> np.ndarray:
    n = int(1.5 * SR)
    t = t_axis(n / SR)
    brown = lowpass(noise(n, 41), 900)
    growl = tone(n, 92, 78, harmonics=9, noise_mix=0.18, vibrato_hz=6, vibrato_cents=70)
    roar = growl * 0.75 + brown * 1.5
    roar *= am(n, 23, 0.7)
    roar *= env_adsr(n, 0.1, 0.25, 0.9, 0.4)
    roar *= 1 + 0.25 * np.sin(2 * np.pi * 1.7 * t)
    return roar


def tiger() -> np.ndarray:
    n = int(1.35 * SR)
    t = t_axis(n / SR)
    rasp = formant(n, [420, 900, 1800], [1.2, 0.8, 0.45], [180, 260, 340], seed=51)
    growl = tone(n, 118, 96, harmonics=8, noise_mix=0.3, vibrato_hz=7, vibrato_cents=55)
    out = growl * 0.8 + rasp * 1.1
    out *= am(n, 27, 0.75)
    out *= env_adsr(n, 0.12, 0.3, 0.8, 0.35)
    out *= 1 + 0.2 * np.sin(2 * np.pi * 2.1 * t)
    return out


def monkey() -> np.ndarray:
    def chirp(f0: float, f1: float, dur: float) -> np.ndarray:
        n = int(dur * SR)
        phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
        out = np.sin(phase) + 0.4 * np.sin(phase * 2) + 0.18 * np.sin(phase * 3)
        out *= env_adsr(n, 0.01, 0.02, 0.7, 0.05)
        return out

    return concat(
        chirp(1500, 2500, 0.13),
        silence(0.05),
        chirp(2400, 1300, 0.16),
        silence(0.07),
        chirp(1600, 2600, 0.12),
    )


def elephant() -> np.ndarray:
    n = int(1.35 * SR)
    t = t_axis(n / SR)
    phase = 2 * np.pi * np.cumsum(np.linspace(300, 1500, n)) / SR
    out = np.zeros(n)
    for h, amp in ((1, 1.0), (2, 0.8), (3, 0.55), (4, 0.35), (5, 0.2), (6, 0.12)):
        out += amp * np.sin(phase * h)
    out /= 3.0
    out += formant(n, [1100, 2400], [0.35, 0.2], [320, 420], seed=61) * 0.5
    out *= am(n, 17, 0.45)
    out *= env_adsr(n, 0.08, 0.2, 0.85, 0.3)
    out *= 1 + 0.14 * np.sin(2 * np.pi * 3.2 * t)
    return out


def duck() -> np.ndarray:
    def quack() -> np.ndarray:
        n = int(0.19 * SR)
        body = tone(n, 330, 290, harmonics=5, noise_mix=0.35)
        body += formant(n, [850, 1700], [0.55, 0.3], [240, 320], seed=71) * 0.8
        body *= am(n, 32, 0.55)
        body *= env_adsr(n, 0.008, 0.03, 0.7, 0.07)
        return body

    return concat(quack(), silence(0.03), quack(), silence(0.03), quack() * 0.9)


def chicken() -> np.ndarray:
    def cluck() -> np.ndarray:
        n = int(0.17 * SR)
        body = tone(n, 700, 420, harmonics=4, noise_mix=0.3)
        body += formant(n, [1600, 2600], [0.5, 0.3], [300, 400], seed=81) * 0.6
        body *= am(n, 36, 0.6)
        body *= env_adsr(n, 0.006, 0.04, 0.6, 0.06)
        return body

    return concat(cluck(), silence(0.05), cluck(), silence(0.06), cluck() * 0.85)


def horse() -> np.ndarray:
    def whinny(dur: float, f0: float, f1: float, noise: float) -> np.ndarray:
        n = int(dur * SR)
        phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
        out = np.zeros(n)
        for h, amp in ((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2)):
            out += amp * np.sin(phase * h)
        out /= 2.1
        out = out * (1 - noise) + formant(n, [900, 1800], [1.0, 0.6], [280, 360], seed=91) * noise
        out *= am(n, 28, 0.6)
        out *= env_adsr(n, 0.05, 0.1, 0.8, 0.12)
        return out

    return concat(
        whinny(0.32, 420, 1000, 0.5),
        silence(0.05),
        whinny(0.62, 1000, 420, 0.45),
    )


def sheep() -> np.ndarray:
    n = int(0.75 * SR)
    base = tone(n, 420, 380, harmonics=6, vibrato_hz=13, vibrato_cents=90)
    base += formant(n, [700, 1500], [0.55, 0.25], [200, 300], seed=101) * 0.5
    base *= env_adsr(n, 0.06, 0.1, 0.8, 0.2)
    return base


def goat() -> np.ndarray:
    n = int(0.9 * SR)
    base = tone(n, 520, 430, harmonics=7, vibrato_hz=11, vibrato_cents=120)
    base += formant(n, [1100, 2200], [0.6, 0.3], [240, 340], seed=111) * 0.6
    base *= env_adsr(n, 0.05, 0.12, 0.82, 0.24)
    return base


def wolf() -> np.ndarray:
    n = int(1.9 * SR)
    phase = 2 * np.pi * np.cumsum(np.linspace(300, 620, n)) / SR
    out = np.zeros(n)
    for h, amp in ((1, 1.0), (2, 0.45), (3, 0.3), (4, 0.16), (5, 0.1)):
        out += amp * np.sin(phase * h)
    out /= 2.0
    out += formant(n, [700, 1400], [0.4, 0.22], [240, 320], seed=121) * 0.4
    t = t_axis(n / SR)
    out *= env_adsr(n, 0.3, 0.3, 0.9, 0.5)
    out *= 1 + 0.05 * np.sin(2 * np.pi * 5.0 * t)
    return out


def frog() -> np.ndarray:
    n = int(0.85 * SR)
    croak = formant(n, [380, 900], [1.4, 0.7], [120, 200], seed=131)
    pulse = np.sign(np.sin(2 * np.pi * 42 * t_axis(n / SR)))
    out = croak * (0.35 + 0.65 * np.abs(pulse))
    out *= env_adsr(n, 0.02, 0.05, 0.85, 0.12)
    return out


def bird() -> np.ndarray:
    def chirp(f0: float, f1: float, dur: float) -> np.ndarray:
        n = int(dur * SR)
        phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
        out = np.sin(phase) + 0.25 * np.sin(phase * 2)
        out *= env_adsr(n, 0.008, 0.02, 0.7, 0.04)
        return out

    return concat(
        chirp(2600, 3900, 0.1),
        silence(0.05),
        chirp(3800, 2700, 0.12),
        silence(0.05),
        chirp(2900, 3500, 0.09),
    )


def pig() -> np.ndarray:
    def grunt() -> np.ndarray:
        n = int(0.26 * SR)
        body = tone(n, 190, 150, harmonics=6, noise_mix=0.45)
        body += formant(n, [600, 1300], [0.6, 0.3], [200, 280], seed=141)
        body *= am(n, 26, 0.6)
        body *= env_adsr(n, 0.02, 0.06, 0.7, 0.1)
        return body

    return concat(grunt(), silence(0.04), grunt() * 0.9)


def donkey() -> np.ndarray:
    n = int(1.0 * SR)
    phase = 2 * np.pi * np.cumsum(np.linspace(700, 380, n)) / SR
    out = np.zeros(n)
    for h, amp in ((1, 1.0), (2, 0.7), (3, 0.45), (4, 0.25)):
        out += amp * np.sin(phase * h)
    out /= 2.4
    out += formant(n, [900, 1900], [0.9, 0.5], [280, 380], seed=151) * 0.8
    out *= am(n, 32, 0.7)
    out *= env_adsr(n, 0.05, 0.15, 0.8, 0.25)
    return out


def rooster() -> np.ndarray:
    def note(f: float, dur: float) -> np.ndarray:
        n = int(dur * SR)
        phase = 2 * np.pi * np.cumsum(np.linspace(f * 0.95, f, n)) / SR
        out = np.zeros(n)
        for h, amp in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)):
            out += amp * np.sin(phase * h)
        out /= 2.0
        out += formant(n, [1100, 2300], [0.5, 0.3], [280, 360], seed=161) * 0.5
        out *= env_adsr(n, 0.02, 0.05, 0.75, 0.08)
        return out

    return concat(
        note(520, 0.16),
        note(700, 0.16),
        note(880, 0.22),
        note(640, 0.2),
        note(430, 0.26),
    )


def owl() -> np.ndarray:
    def hoot(dur: float) -> np.ndarray:
        n = int(dur * SR)
        body = tone(n, 400, 370, harmonics=4, noise_mix=0.18)
        body += formant(n, [800, 1500], [0.35, 0.2], [220, 300], seed=171) * 0.4
        body *= env_adsr(n, 0.09, 0.12, 0.7, 0.3)
        return body

    return concat(hoot(0.42), silence(0.14), hoot(0.5) * 0.9)


def bee() -> np.ndarray:
    n = int(1.5 * SR)
    base = tone(n, 195, 190, harmonics=8, noise_mix=0.25)
    out = base * am(n, 24, 0.85)
    out += formant(n, [1200, 2400], [0.2, 0.12], [300, 400], seed=181) * 0.3
    out *= env_adsr(n, 0.1, 0.1, 0.9, 0.3)
    return out


# --------------------------------------------------------------------------
# interface sounds
# --------------------------------------------------------------------------
def ui_start() -> np.ndarray:
    n = int(0.28 * SR)
    t = t_axis(n / SR)
    out = tone(n, 880, 1320, harmonics=3)
    out *= env_adsr(n, 0.006, 0.05, 0.5, 0.16)
    out += tone(n, 1760, 1980, harmonics=1) * 0.25 * np.exp(-t * 9)
    return out


def ui_error() -> np.ndarray:
    n = int(0.45 * SR)
    out = tone(n, 420, 180, harmonics=5, noise_mix=0.15)
    out *= env_adsr(n, 0.008, 0.1, 0.5, 0.25)
    return out


def ui_chime() -> np.ndarray:
    n = int(0.6 * SR)
    t = t_axis(n / SR)
    out = np.zeros(n)
    for f, delay in ((880, 0.0), (1320, 0.09), (1760, 0.18)):
        m = int(delay * SR)
        if m >= n:
            continue
        seg = tone(n - m, f, f, harmonics=3)
        out[m:] += seg * np.exp(-t[: n - m] * 4.5)
    return out


VOICES = {
    "dog": dog,
    "cat": cat,
    "cow": cow,
    "lion": lion,
    "tiger": tiger,
    "monkey": monkey,
    "elephant": elephant,
    "duck": duck,
    "chicken": chicken,
    "horse": horse,
    "sheep": sheep,
    "goat": goat,
    "wolf": wolf,
    "frog": frog,
    "bird": bird,
    "pig": pig,
    "donkey": donkey,
    "rooster": rooster,
    "owl": owl,
    "bee": bee,
    "start": ui_start,
    "error": ui_error,
    "chime": ui_chime,
}


def main() -> int:
    print(f"Generating NEX sound assets into {OUT}")
    for name, fn in VOICES.items():
        try:
            save(name, fn())
        except Exception as exc:  # noqa: BLE001
            print(f"  !! {name}: {exc}", file=sys.stderr)
            return 1
    print(f"Done — {len(VOICES)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
