// Records docs/demo.gif, the README walkthrough of /demo. Needs the dev
// server on :5174 and playwright-core (install it anywhere outside the
// project, e.g. a temp dir, and run this from there):
//
//   node record-demo-gif.mjs
//   ffmpeg -f concat -safe 0 -i frames.txt -vf "fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -loop 0 demo.gif
//
// Keep it under 4 MB; drop fps before width if it grows.
import { chromium } from "playwright-core";

const W = 1280, H = 800;
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const ctx = await browser.newContext({
  viewport: { width: W, height: H },
  colorScheme: "light",
});
const page = await ctx.newPage();
const pause = (ms) => page.waitForTimeout(ms);

// Chrome's own screencast: a frame per repaint with its timestamp, written
// out with durations for ffmpeg's concat demuxer.
import fs from "node:fs";
fs.rmSync("frames", { recursive: true, force: true });
fs.mkdirSync("frames");
const cdp = await ctx.newCDPSession(page);
const frames = [];
cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
  const file = `frames/${String(frames.length).padStart(5, "0")}.jpg`;
  fs.writeFileSync(file, Buffer.from(data, "base64"));
  frames.push({ file, t: metadata.timestamp });
  await cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
});

async function glide(px, steps = 30) {
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, px / steps);
    await pause(30);
  }
}

await page.goto("http://localhost:5174/demo", { waitUntil: "networkidle" });
await pause(600);
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, everyNthFrame: 1 });
await pause(2500);              // headline + "lost to holding"
await page.mouse.move(1272, 400); // the gutter: wheel scrolls, no chart tooltips
await glide(560);               // metrics
await pause(1800);
await glide(560);               // cost tolerance + equity curve
await pause(2200);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
await pause(1000);
await page.getByRole("tab", { name: /Validation/ }).click();
await pause(800);
await glide(420);               // verdict: 2 of 6 checks
await pause(2600);
await page.getByText("Show the working").click();
await page.mouse.move(1272, 400);
await pause(1200);
await glide(450);
await pause(2200);
await glide(450);
await pause(2200);
await glide(450);
await pause(2000);
await cdp.send("Page.stopScreencast");
const lines = frames.map((f, i) => {
  const next = frames[i + 1]?.t ?? f.t + 1.5;
  return `file '${f.file}'\nduration ${(next - f.t).toFixed(3)}`;
});
fs.writeFileSync("frames.txt", lines.join("\n") + `\nfile '${frames.at(-1).file}'\n`);
console.log(frames.length, "frames", (frames.at(-1).t - frames[0].t).toFixed(1), "s");
await ctx.close();
await browser.close();
console.log("done");
