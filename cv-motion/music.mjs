// ============================================================================
//  Procedural soundtrack — a lo-fi groove synthesised from scratch in code.
//  Every sound (pad, keys, bass, arp, drums, the "block landing" ticks) is
//  generated here; the ticks are driven by the exact build timeline the
//  studio exports, so the audio locks to the animation frame by frame.
//
//  Usage (standalone):  node music.mjs events.json out.wav
//  Usage (module):      generateMusic({ duration, events }) -> { left, right, sampleRate }
// ============================================================================
import fs from "node:fs";

const SR = 48000;
const TAU = Math.PI * 2;
const midiHz = m => 440 * Math.pow(2, (m - 69) / 12);

function mulberry32(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

class Bus {
  constructor(n) { this.L = new Float32Array(n); this.R = new Float32Array(n); this.n = n; }
  // add a mono signal generator over [t0, t0+len) with a pan in [-1, 1]
  add(t0, len, gen, gain = 1, pan = 0) {
    const s0 = Math.max(0, Math.floor(t0 * SR)), s1 = Math.min(this.n, Math.floor((t0 + len) * SR));
    const gl = gain * Math.cos((pan + 1) * Math.PI / 4), gr = gain * Math.sin((pan + 1) * Math.PI / 4);
    for (let i = s0; i < s1; i++) { const v = gen((i - s0) / SR); this.L[i] += v * gl; this.R[i] += v * gr; }
  }
  mixInto(other, g = 1) { for (let i = 0; i < this.n; i++) { other.L[i] += this.L[i] * g; other.R[i] += this.R[i] * g; } }
}

function lowpass(arr, fc) { const a = 1 - Math.exp(-TAU * fc / SR); let y = 0; for (let i = 0; i < arr.length; i++) { y += a * (arr[i] - y); arr[i] = y; } }
function highpass(arr, fc) { const a = 1 - Math.exp(-TAU * fc / SR); let y = 0; for (let i = 0; i < arr.length; i++) { y += a * (arr[i] - y); arr[i] = arr[i] - y; } }

// Schroeder reverb, small room, applied to a copy and mixed back
function reverb(bus, mix) {
  const combs = [0.0297, 0.0371, 0.0411, 0.0437], fb = 0.74;
  for (const ch of ["L", "R"]) {
    const x = bus[ch]; const wet = new Float32Array(x.length);
    for (const d of combs) {
      const D = Math.floor(d * SR * (ch === "R" ? 1.07 : 1)); const buf = new Float32Array(D); let p = 0, lp = 0;
      for (let i = 0; i < x.length; i++) { const out = buf[p]; lp += 0.4 * (out - lp); buf[p] = x[i] + lp * fb; p = (p + 1) % D; wet[i] += out * 0.25; }
    }
    for (const d of [0.005, 0.0017]) {
      const D = Math.floor(d * SR); const buf = new Float32Array(D); let p = 0; const g = 0.7;
      for (let i = 0; i < wet.length; i++) { const b = buf[p]; const v = wet[i] + g * b; buf[p] = v; wet[i] = b - g * v; p = (p + 1) % D; }
    }
    for (let i = 0; i < x.length; i++) x[i] = x[i] * (1 - mix * 0.5) + wet[i] * mix;
  }
}

// ping-pong delay
function pingpong(bus, time, fb, mix) {
  const D = Math.floor(time * SR); const n = bus.n; const L = bus.L.slice(), R = bus.R.slice();
  const dl = new Float32Array(n), dr = new Float32Array(n);
  for (let i = D; i < n; i++) { dl[i] = (R[i - D] + dr[i - D]) * fb; dr[i] = (L[i - D] + dl[i - D]) * fb; }
  for (let i = 0; i < n; i++) { bus.L[i] += dl[i] * mix / fb; bus.R[i] += dr[i] * mix / fb; }
}

export function generateMusic({ duration = 60, events = [] } = {}) {
  const n = Math.ceil(duration * SR);
  const rnd = mulberry32(2024);
  const BPM = 100, beat = 60 / BPM, bar = beat * 4;
  const bars = Math.ceil(duration / bar);
  // I – iii – vi – IV in F major, lo-fi voicings
  const PROG = [
    { pad: [53, 57, 60, 64], keys: [60, 64, 69], bass: 41 },      // Fmaj7
    { pad: [52, 57, 60, 64], keys: [60, 64, 67], bass: 45 },      // Am7
    { pad: [50, 53, 57, 60, 64], keys: [57, 60, 64], bass: 38 },  // Dm9
    { pad: [46, 53, 57, 62], keys: [58, 62, 65], bass: 46 },      // Bbmaj7
  ];
  const phases = events.filter(e => e.kind === "intro" || e.kind === "stop" || e.kind === "outro");
  const grooveStart = (phases.find(e => e.kind === "stop") || { t: 6 }).t;
  const outroStart = (phases.find(e => e.kind === "outro") || { t: duration - 7 }).t;
  const grooveEnd = outroStart + 1.4;

  const pad = new Bus(n), keys = new Bus(n), bass = new Bus(n), arp = new Bus(n), drums = new Bus(n), hats = new Bus(n), ticks = new Bus(n), fx = new Bus(n);

  for (let b = 0; b < bars; b++) {
    const t0 = b * bar; if (t0 >= duration) break;
    const ch = b === bars - 1 ? PROG[0] : PROG[b % 4];
    // ---- pad: warm additive voices, slow attack, overlaps into the next bar
    for (const m of ch.pad) {
      const f = midiHz(m); const det = 1 + (rnd() - 0.5) * 0.004;
      pad.add(t0, bar + 0.9, t => {
        const env = Math.min(1, t / 0.6) * (t > bar ? Math.max(0, 1 - (t - bar) / 0.9) : 1);
        return env * (Math.sin(TAU * f * t) + 0.5 * Math.sin(TAU * f * det * t + 0.3) + 0.22 * Math.sin(TAU * 2 * f * t) + 0.08 * Math.sin(TAU * 3 * f * t));
      }, 0.035, (m % 7) / 7 - 0.5);
    }
    // ---- keys: rhodes-ish stabs on 1, the "and" of 2, and 4
    const hits = [[0, 1], [1.5, 0.65], [3, 0.8]];
    for (const [bt, vel] of hits) {
      const th = t0 + bt * beat; if (th > duration - 0.5) continue;
      ch.keys.forEach((m, i) => {
        const f = midiHz(m);
        keys.add(th, 1.6, t => { const env = Math.exp(-t / 0.55); const fm = Math.exp(-t / 0.18) * 0.9; return env * Math.sin(TAU * f * t + fm * Math.sin(TAU * 2 * f * t)) * (1 + 0.08 * Math.sin(TAU * 5.5 * t)); }, 0.06 * vel, i / 2 - 0.5);
      });
    }
    // ---- bass: root on 1 and the "and" of 3, fifth on 4 every other bar
    const bnotes = [[0, ch.bass, 1], [2.5, ch.bass, 0.8]]; if (b % 2 === 1) bnotes.push([3.5, ch.bass + 7, 0.6]);
    for (const [bt, m, vel] of bnotes) {
      const th = t0 + bt * beat; if (th < grooveStart - 0.1 || th > grooveEnd) continue; const f = midiHz(m);
      bass.add(th, 0.7, t => { const env = Math.min(1, t / 0.006) * Math.exp(-t / 0.32); return env * Math.tanh(1.8 * (Math.sin(TAU * f * t) + 0.45 * Math.sin(TAU * 2 * f * t))); }, 0.2 * vel, 0);
    }
    // ---- arp: eighth-note plucks climbing through the chord
    const tones = ch.keys; const pattern = [tones[0], tones[1], tones[2], tones[1] + 12, tones[2] + 12, tones[1] + 12, tones[2], tones[0] + 12];
    for (let s = 0; s < 8; s++) {
      const th = t0 + s * beat / 2; if (th < grooveStart || th > grooveEnd) continue;
      const m = pattern[s]; const f = midiHz(m); const vel = s % 4 === 0 ? 1 : 0.7;
      arp.add(th, 0.35, t => { const env = Math.exp(-t / 0.11); return env * (Math.sin(TAU * f * t) + 0.25 * Math.sin(TAU * 3 * f * t)); }, 0.05 * vel, s % 2 ? 0.45 : -0.45);
    }
    // ---- drums
    const kicks = [0, 2]; if (b % 2 === 1) kicks.push(2.75);
    for (const bt of kicks) {
      const th = t0 + bt * beat; if (th < grooveStart - 0.05 || th > grooveEnd) continue;
      drums.add(th, 0.35, t => { const fr = 42 + 80 * Math.exp(-t / 0.045); const env = Math.exp(-t / 0.16); return env * Math.sin(TAU * fr * t) * 1.1 + (t < 0.004 ? (rnd() - 0.5) * 0.6 : 0); }, 0.5, 0);
    }
    for (const bt of [1, 3]) {
      const th = t0 + bt * beat; if (th < grooveStart - 0.05 || th > grooveEnd) continue;
      drums.add(th, 0.25, t => { const env = Math.exp(-t / 0.07); return env * ((rnd() - 0.5) * 1.2 + 0.6 * Math.sin(TAU * 185 * t) * Math.exp(-t / 0.045)); }, 0.13, 0.1);
    }
    for (let s = 0; s < 8; s++) {
      const th = t0 + s * beat / 2; if (th < grooveStart || th > grooveEnd) continue;
      const open = s === 7; const tau = open ? 0.13 : 0.028;
      hats.add(th, open ? 0.4 : 0.09, t => { const env = Math.exp(-t / tau); return env * (rnd() - 0.5) * 2; }, (s % 2 ? 0.028 : 0.042), -0.2);
    }
  }
  highpass(drums.L, 30); highpass(drums.R, 30); lowpass(drums.L, 5500); lowpass(drums.R, 5500);
  highpass(hats.L, 6500); highpass(hats.R, 6500); hats.mixInto(drums, 1);

  // ---- block-landing ticks, from the animation's own build schedule
  const scale = [77, 79, 81, 84, 86, 89, 91, 93, 96, 98]; // F major pentatonic, two octaves
  const byStop = new Map();
  for (const e of events) {
    if (!["platform", "prop", "board", "char", "path"].includes(e.kind)) continue;
    if (!byStop.has(e.stop)) byStop.set(e.stop, []); byStop.get(e.stop).push(e);
  }
  for (const [, list] of byStop) {
    list.sort((a, b) => a.t - b.t);
    let last = -1, idx = 0; const charEvents = list.filter(e => e.kind === "char");
    for (const e of list) {
      if (e.t - last < 0.055) continue; last = e.t;
      const m = scale[idx % scale.length] + (e.kind === "char" ? 7 : e.kind === "path" ? -12 : 0); idx++;
      const f = midiHz(m); const g = e.kind === "path" ? 0.02 : e.kind === "platform" ? 0.028 : 0.038;
      ticks.add(e.t, 0.12, t => { const env = Math.exp(-t / 0.035); return env * (Math.sin(TAU * f * t) + 0.3 * Math.sin(TAU * 2.76 * f * t) * Math.exp(-t / 0.012)); }, g, (idx % 2 ? 0.3 : -0.3));
    }
    if (charEvents.length) { // completion chime when the twin's head lands
      const te = charEvents[charEvents.length - 1].t; const f = midiHz(101);
      ticks.add(te, 0.9, t => Math.exp(-t / 0.3) * (Math.sin(TAU * f * t) + 0.4 * Math.sin(TAU * f * 2 * t) * Math.exp(-t / 0.1)), 0.05, 0.2);
    }
  }
  // ---- whoosh risers into each stop + a soft crash on arrival
  for (const e of phases) {
    if (e.kind !== "stop" && e.kind !== "outro") continue;
    fx.add(e.t - 0.9, 0.9, t => { const k = t / 0.9; return Math.pow(k, 2.2) * (rnd() - 0.5) * 2; }, 0.045, 0);
    fx.add(e.t, 0.9, t => Math.exp(-t / 0.28) * (rnd() - 0.5) * 2, 0.045, 0);
  }
  lowpass(fx.L, 2500); lowpass(fx.R, 2500);
  lowpass(pad.L, 1400); lowpass(pad.R, 1400);

  // ---- buses, effects, master
  const wet = new Bus(n); keys.mixInto(wet, 1); arp.mixInto(wet, 1); ticks.mixInto(wet, 1); fx.mixInto(wet, 1);
  pingpong(wet, beat * 0.75, 0.32, 0.18);
  pad.mixInto(wet, 0.6);
  reverb(wet, 0.16);
  const master = new Bus(n); wet.mixInto(master, 1); pad.mixInto(master, 0.4); bass.mixInto(master, 1); drums.mixInto(master, 1);
  // gentle "lo-fi" tone: roll off the very top
  lowpass(master.L, 11000); lowpass(master.R, 11000);
  // soft clip + fades + normalise
  let peak = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR; const fade = Math.min(1, t / 0.4) * Math.min(1, Math.max(0, (duration - t) / 2.6));
    master.L[i] = Math.tanh(master.L[i] * 1.25) / 1.25 * fade; master.R[i] = Math.tanh(master.R[i] * 1.25) / 1.25 * fade;
    peak = Math.max(peak, Math.abs(master.L[i]), Math.abs(master.R[i]));
  }
  const g = 0.89 / (peak || 1);
  for (let i = 0; i < n; i++) { master.L[i] *= g; master.R[i] *= g; }
  return { left: master.L, right: master.R, sampleRate: SR };
}

export function writeWav(path, { left, right, sampleRate }) {
  const n = left.length; const buf = Buffer.alloc(44 + n * 4);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 4, 4); buf.write("WAVE", 8); buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(sampleRate, 24);
  buf.writeUInt32LE(sampleRate * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34); buf.write("data", 36); buf.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i++) { buf.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(left[i] * 32767))), 44 + i * 4); buf.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(right[i] * 32767))), 46 + i * 4); }
  fs.writeFileSync(path, buf);
}

if (process.argv[1] && process.argv[1].endsWith("music.mjs")) {
  const [evPath, out] = process.argv.slice(2);
  const ev = evPath ? JSON.parse(fs.readFileSync(evPath, "utf8")) : { duration: 60, events: [] };
  writeWav(out || "music.wav", generateMusic(ev));
  console.log("wrote", out || "music.wav");
}
