// ============================================================================
//  Renders studio.html to an MP4 — deterministically, frame by frame.
//
//    node render.mjs                       -> output/mohammad-nasravi-cv.mp4
//    node render.mjs --workers 4           -> parallel headless pages
//    node render.mjs --out my.mp4 --seconds 12   (quick preview of the first 12 s)
//    node render.mjs --no-audio
//
//  Needs: Node 18+, ffmpeg on PATH, playwright (npm i playwright) with Chromium.
// ============================================================================
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generateMusic, writeWav } from "./music.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith("--") ? [a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : true] : []).filter(Boolean));
const OUT = path.resolve(args.out || path.join(here, "output", "mohammad-nasravi-cv.mp4"));
const WORKERS = Math.max(1, parseInt(args.workers || Math.min(4, os.cpus().length), 10));
const AUDIO = !args["no-audio"];
const SECONDS = args.seconds ? parseFloat(args.seconds) : null;
const CRF = args.crf || "18";
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cvmotion-"));
const pageUrl = "file://" + path.join(here, "studio.html") + "?render=1";

const log = (...m) => console.log(new Date().toISOString().slice(11, 19), ...m);

function run(cmd, cmdArgs) {
  return new Promise((res, rej) => { const p = spawn(cmd, cmdArgs, { stdio: ["ignore", "inherit", "inherit"] }); p.on("exit", c => c === 0 ? res() : rej(new Error(cmd + " exited " + c))); });
}

async function openPage(browser, w, h) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on("pageerror", e => console.error("page error:", e.message));
  await page.goto(pageUrl);
  await page.evaluate(() => window.CV_STUDIO.ready);
  return page;
}

async function renderSegment(browser, idx, f0, f1, video) {
  const page = await openPage(browser, video.width, video.height);
  const seg = path.join(tmp, `seg-${String(idx).padStart(2, "0")}.mp4`);
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(video.fps), "-i", "pipe:0",
    "-c:v", "libx264", "-preset", "slow", "-crf", CRF, "-pix_fmt", "yuv420p", "-r", String(video.fps), "-g", String(video.fps * 2), "-an", seg], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("exit", c => c === 0 ? res() : rej(new Error("ffmpeg segment failed"))));
  for (let f = f0; f < f1; f++) {
    const t = f / video.fps;
    const dataUrl = await page.evaluate(t => window.CV_STUDIO.frameDataURL(t), t);
    const buf = Buffer.from(dataUrl.slice(dataUrl.indexOf(",") + 1), "base64");
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if ((f - f0) % 60 === 0) log(`worker ${idx}: frame ${f}/${f1} (${(t).toFixed(1)}s)`);
  }
  ff.stdin.end();
  await done;
  await page.close();
  return seg;
}

(async () => {
  const browser = await chromium.launch();
  const probe = await openPage(browser, 320, 180);
  const cfg = await probe.evaluate(() => window.CV_STUDIO.config);
  const events = await probe.evaluate(() => window.CV_STUDIO.events());
  await probe.close();
  const video = { ...cfg.video };
  const duration = SECONDS ? Math.min(SECONDS, video.duration) : video.duration;
  const totalFrames = Math.round(duration * video.fps);
  log(`rendering ${totalFrames} frames @ ${video.fps}fps, ${video.width}x${video.height}, ${WORKERS} worker(s)`);

  let wav = null;
  if (AUDIO) {
    log("synthesising soundtrack…");
    fs.writeFileSync(path.join(tmp, "events.json"), JSON.stringify({ duration: video.duration, events }));
    wav = path.join(tmp, "music.wav");
    writeWav(wav, generateMusic({ duration: video.duration, events }));
    log("soundtrack done");
  }

  const per = Math.ceil(totalFrames / WORKERS);
  const jobs = [];
  for (let w = 0; w < WORKERS; w++) { const f0 = w * per, f1 = Math.min(totalFrames, f0 + per); if (f0 < f1) jobs.push(renderSegment(browser, w, f0, f1, video)); }
  const segs = await Promise.all(jobs);
  await browser.close();

  const list = path.join(tmp, "list.txt");
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join("\n"));
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const ffArgs = ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list];
  if (wav) ffArgs.push("-i", wav);
  ffArgs.push("-c:v", "copy");
  if (wav) ffArgs.push("-c:a", "aac", "-b:a", "192k", "-t", String(duration));
  ffArgs.push("-movflags", "+faststart", OUT);
  await run("ffmpeg", ffArgs);
  fs.rmSync(tmp, { recursive: true, force: true });
  log("done →", OUT, `(${(fs.statSync(OUT).size / 1e6).toFixed(1)} MB)`);
})().catch(e => { console.error(e); process.exit(1); });
