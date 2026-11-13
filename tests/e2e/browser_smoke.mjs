// End-to-end check of the browser game with the "Rude Politic" fighter (spec 002, SC-2..SC-6).
//   node tests/e2e/browser_smoke.mjs            (needs google-chrome and python3; starts its own static server)
// Env: SHOTS=<dir> saves screenshots of key moments.
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const HTTP = 8777, CDP = 9333;
const procs = [];
const sleep = ms => new Promise(r => setTimeout(r, ms));
let failures = 0;
const check = (name, ok, extra = "") => { console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : "  -> " + extra}`); if (!ok) failures++; };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

procs.push(spawn("python3", ["-m", "http.server", String(HTTP)], { cwd: ROOT, stdio: "ignore" }));
procs.push(spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu", `--remote-debugging-port=${CDP}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "chrome-e2e-"))}`, "--window-size=1280,720", "about:blank"], { stdio: "ignore" }));
const cleanup = () => procs.forEach(p => p.kill());
process.on("exit", cleanup);

let tab;
for (let i = 0; i < 50 && !tab; i++) {
  await sleep(200);
  try { tab = (await (await fetch(`http://127.0.0.1:${CDP}/json`)).json()).find(t => t.type === "page"); } catch { /* not up yet */ }
}
if (!tab) { console.log("FAIL  could not reach Chrome"); process.exit(1); }
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener("open", r));
let id = 0; const pending = new Map(); const consoleErrors = [];
ws.addEventListener("message", ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  else if (m.method === "Runtime.exceptionThrown") consoleErrors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") consoleErrors.push(m.params.args.map(a => a.value).join(" "));
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const run = async expr => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || "eval failed: " + expr);
  return r.result.result.value;
};
const shot = async name => {
  if (!process.env.SHOTS) return;
  mkdirSync(process.env.SHOTS, { recursive: true });
  const r = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(process.env.SHOTS, name + ".png"), Buffer.from(r.result.data, "base64"));
};
await send("Runtime.enable"); await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: `http://127.0.0.1:${HTTP}/index.html` });

// ---- helpers living inside the page --------------------------------------------------------------
await sleep(2500);
await run(`window.T = {
  fi: f => f.char.sprite.frames.indexOf(f.frame),
  tick(n = 1, each) { const out = []; for (let i = 0; i < n; i++) { update(); out.push(each ? each() : 0); } return out; },
  begin(c1, c2) { startFight({ p1: ROSTER.find(r => r.id === c1), p2: ROSTER.find(r => r.id === c2) }); screen = "test"; keys.clear(); },
  far() { p1.x = 200; p2.x = 900; p2.facing = -1; },     // out of reach of each other
  near(d = 150) { p1.x = 300; p2.x = 300 + d; },
  press(code, n = 1) { keys.add(code); update(); keys.delete(code); },
};`);

// ---- 1. roster / select screen --------------------------------------------------------------------
check("select screen is active at load", await run("CharacterSelect.active === true"));
check("roster has 6 fighters incl. Rude Politic and La Gestora", same(await run("ROSTER.map(r => r.id)"), ["dummy", "ministra", "portavoz", "presidente", "rudepolitic", "gestora"]));
check("select screen shows 6 tiles", (await run("document.querySelectorAll('.cs__tile').length")) === 6);
check("La Gestora definition loaded (27 frames, grenade special)", await run("!!CHAR_DEFS.gestora && CHAR_DEFS.gestora.sprite.frames.length === 27 && CHAR_DEFS.gestora.special.kind === 'grenade'"));
check("character definition loaded", await run("!!CHAR_DEFS.rudepolitic && CHAR_DEFS.rudepolitic.sprite.frames.length === 26"));
check("panel shows 'Golpe Español' after navigating to it", await (async () => {
  await run(`(() => { const k = (code) => dispatchEvent(new KeyboardEvent("keydown", { code, bubbles: true })); k("KeyS"); k("KeyS"); })()`);
  return (await run(`document.querySelector('.cs__panel[data-player="0"] .cs__special').textContent`)).includes("Golpe Español");
})());
await shot("select");
await run(`(() => { const k = (code) => dispatchEvent(new KeyboardEvent("keydown", { code, bubbles: true })); k("KeyF"); k("ArrowLeft"); k("KeyK"); })()`);
await sleep(2200);
check("both locked in -> fight starts with Rude Politic as P1", await run(`screen === "fight" && p1.char.id === "rudepolitic" && p2.char.id === "default"`));
check("stat modifiers applied (x0.9 speed, x1.2 damage, 110 HP)", await run("Math.abs(p1.stats.speed - 0.9) < 1e-9 && Math.abs(p1.stats.damage - 1.2) < 1e-9 && p1.health === 110 && p1.stats.health === 110"));

// ---- 2. idle + walk -------------------------------------------------------------------------------
await run("T.begin('rudepolitic', 'dummy'); T.far();");
let idle = await run("T.tick(65, () => T.fi(p1))");
check("idle alternates stance frames 6/11 every 30 updates", idle[0] === 6 && idle[29] === 11 && idle[59] === 6 && new Set(idle).size === 2, JSON.stringify(idle.slice(0, 5)));
await run("keys.add('KeyD')");
let walk = await run("T.tick(36, () => T.fi(p1))");
check("walk plays frames 0..5 in order, 6 updates each", same([...new Set(walk)], [0, 1, 2, 3, 4, 5]) && walk.every((v, i) => v === Math.floor(i / 6)), JSON.stringify(walk));
const x0 = await run("p1.x"); await run("T.tick(10)");
check("walk right moves right (3.6 px/update)", Math.abs((await run("p1.x")) - x0 - 36) < 0.01);
await run("keys.delete('KeyD'); keys.add('KeyA')"); const x1 = await run("p1.x"); await run("T.tick(10)");
check("walk left moves left and sprite mirrors via facing", (await run("p1.x")) < x1);
await run("keys.clear(); T.tick(2)");
check("releasing keys returns to idle", (await run("p1.state")) === "idle");

// ---- 3. punch / kick ------------------------------------------------------------------------------
for (const [move, key, total, a0, a1, peak, dmg] of [["punch", "KeyF", 24, 8, 11, 9, 8], ["kick", "KeyG", 28, 10, 14, 13, 11]]) {
  await run("T.begin('rudepolitic', 'dummy'); T.far();");
  await run(`T.press('${key}')`);                        // update #1 (t = 1)
  const seq = await run("T.tick(40, () => [p1.state, p1.t, !!p1.hitbox(), T.fi(p1)])");
  const states = seq.filter(s => s[0] === move).length + 1;   // + the update done by press()
  check(`${move}: lasts exactly ${total} updates then idle`, states === total && seq[total - 1][0] === "idle", `states=${states}`);
  const active = seq.filter(s => s[2]).map(s => s[1]);
  check(`${move}: hitbox only on updates ${a0}-${a1}`, same(active, Array.from({ length: a1 - a0 + 1 }, (_, i) => a0 + i)), JSON.stringify(active));
  check(`${move}: extension frame ${peak} shown while active`, seq.filter(s => s[2]).some(s => s[3] === peak));
  await run("T.begin('rudepolitic', 'dummy'); T.near(130);"); await run("p2.health = 100;");
  await run(`T.press('${key}')`); await run("T.tick(40)");
  const hp = await run("p2.health");
  check(`${move}: connects once for ${Math.round(dmg * 1.2)} damage`, hp === 100 - Math.round(dmg * 1.2), `hp=${hp}`);
}

// ---- 4. jump ---------------------------------------------------------------------------------------
await run("T.begin('rudepolitic', 'dummy'); T.far();");
await run("T.press('KeyW')");
const jump = await run("T.tick(60, () => [p1.state, T.fi(p1), p1.y])");
const seqFrames = jump.map(j => j[1]);
check("jump: takeoff(16) -> rise(17) -> apex(18) -> fall(19)", [16, 17, 18, 19].every(f => seqFrames.includes(f)) && seqFrames.indexOf(16) < seqFrames.indexOf(17) && seqFrames.indexOf(17) < seqFrames.indexOf(18) && seqFrames.indexOf(18) < seqFrames.indexOf(19), JSON.stringify(seqFrames));
check("jump: landing crouch (20) for 6 updates then idle stance", await (async () => {
  const landIdx = seqFrames.indexOf(20); return landIdx > 0 && seqFrames.slice(landIdx, landIdx + 6).every(f => f === 20) && [6, 11].includes(seqFrames[landIdx + 6]);
})(), JSON.stringify(seqFrames));
check("jump: back on the floor in idle", (await run("p1.y === FLOOR_Y && p1.state === 'idle'")));

// ---- 5. Golpe Español -------------------------------------------------------------------------------
await run("T.begin('rudepolitic', 'dummy'); T.near(150); p2.health = 100;");
await run("T.press('KeyH')");
await shot("special-0-raise");
const sp = await run("T.tick(60, () => [p1.state, p1.t, !!p1.hitbox(), T.fi(p1), p2.health, shake, banners.length, particles.length])");
const inSp = sp.filter(s => s[0] === "special");
check("special: 52 updates total, then idle", inSp.length + 1 === 52 && sp[51][0] === "idle", `len=${inSp.length + 1}`);
const order = []; inSp.forEach(s => { if (order[order.length - 1] !== s[3]) order.push(s[3]); });
check("special: frames 21,22,23,24,25 in order (grab, hold, swing, impact, recovery)", same([21, ...order], [21, 21, 22, 23, 24, 25].filter((v, i, a) => i === 0 || v !== a[i - 1]).slice(0, 5)) || same(order, [21, 22, 23, 24, 25]) || same([21, ...order].filter((v, i, a) => i === 0 || v !== a[i - 1]), [21, 22, 23, 24, 25]), JSON.stringify(order));
check("special: hitbox only on updates 27-30", same(sp.filter(s => s[2]).map(s => s[1]), [27, 28, 29, 30]), JSON.stringify(sp.filter(s => s[2]).map(s => s[1])));
check("special: opponent loses 26 HP (22 x 1.2), exactly once", (await run("p2.health")) === 74 && sp.filter((s, i) => i && s[4] < sp[i - 1][4]).length === 1, `hp=${await run("p2.health")}`);
check("special: impact feedback (shake >= 18, particles, banner)", sp.some(s => s[5] >= 18) && sp.some(s => s[7] > 20) && sp.some(s => s[6] === 1));
check("special: not a projectile", (await run("projectiles.length")) === 0);
// screenshots of the key moments
await run("T.begin('rudepolitic', 'dummy'); T.near(150);"); await run("T.press('KeyH'); T.tick(24)"); await shot("special-1-swing");
await run("T.tick(4)"); await shot("special-2-impact"); await run("T.tick(12)"); await shot("special-3-recovery");
await run("T.begin('rudepolitic', 'dummy'); T.near(150); T.press('KeyG'); T.tick(11)"); await shot("kick");
// can be started in the air: keeps falling, lands, finishes, and still hurts
await run("T.begin('rudepolitic', 'dummy'); T.near(150); p2.health = 100; T.press('KeyW'); T.tick(10);");
await run("keys.add('KeyH'); T.tick(1); keys.clear()");
check("special: can be cast in the air", (await run("p1.state")) === "special" && (await run("p1.airborne")));
const air = await run("T.tick(70, () => [p1.state, p1.y, !!p1.hitbox(), p1.t])");
check("air special: falls with gravity, lands, finishes and returns to idle", await run("p1.y === FLOOR_Y && p1.state === 'idle' && !p1.airborne"), JSON.stringify(air.slice(-3)));
check("air special: lands its hitbox only during the active window", air.filter(a => a[2]).every(a => a[3] >= 27 && a[3] <= 30));
await run("T.begin('rudepolitic', 'dummy'); T.near(150); p2.health = 100; T.press('KeyW'); T.tick(4); keys.add('KeyH'); T.tick(1); keys.clear(); T.tick(60)");
check("air special: connects for 26 damage if the opponent is in front", (await run("p2.health")) === 74, `hp=${await run("p2.health")}`);
// cannot be cancelled by the owner's own input
await run("T.begin('rudepolitic', 'dummy'); T.far(); T.press('KeyH'); T.tick(5); keys.add('KeyW'); keys.add('KeyF'); keys.add('KeyG'); T.tick(10);");
check("special: cannot be cancelled into jump/punch/kick", (await run("p1.state === 'special' && p1.y === FLOOR_Y")));
await run("keys.clear()");
// a hit interrupts it (like every other state)
await run("T.begin('rudepolitic', 'dummy'); T.near(130); T.press('KeyH'); T.tick(6); p1.takeHit(5, 10, p2.x); T.tick(1)");
check("special: interrupted only by taking a hit", (await run("p1.state")) === "hit");
// not clashable: slam vs punch trades instead of cancelling
await run("T.begin('rudepolitic', 'dummy'); T.near(110); p1.health = p1.stats.health; p2.health = 100;");
// P2's punch (updates 28-30) is active on the SAME update as the slam's first active update (28): a clashable
// move would cancel both (hp stays 100); the slam must land instead.
await run("T.press('KeyH'); T.tick(21); T.press('KeyK'); T.tick(20)");
check("special: not clashable by a simultaneous punch (still lands)", (await run("p2.health")) === 74, `hp=${await run("p2.health")}`);

// ---- 7. La Gestora: basics, punch/kick timing, and "Gestión de Mierda" (grenade) -------------------------
const GR = "gestora";
await run(`T.begin('${GR}', 'dummy'); T.far();`);
check("La Gestora: stats 4/3/3 -> speed x1.1, damage x1.0, 100 HP", await run("Math.abs(p1.stats.speed - 1.1) < 1e-9 && p1.stats.damage === 1 && p1.health === 100"));
const gIdle = await run("T.tick(65, () => T.fi(p1))");
check("La Gestora idle alternates stance frames 6/11 every 30 updates", gIdle[0] === 6 && gIdle[29] === 11 && gIdle[59] === 6, JSON.stringify(gIdle.slice(0, 3)));
await run("keys.add('KeyD')");
const gWalk = await run("T.tick(36, () => T.fi(p1))");
await run("keys.clear(); T.tick(2)");
check("La Gestora walk plays frames 0..5, 6 updates each", gWalk.every((v, i) => v === Math.floor(i / 6)), JSON.stringify(gWalk));
check("La Gestora returns to idle after walking", (await run("p1.state")) === "idle");

for (const [move, key, total, a0, a1, peak, dmg] of [["punch", "KeyF", 20, 7, 10, 8, 8], ["kick", "KeyG", 25, 9, 13, 13, 11]]) {
  await run(`T.begin('${GR}', 'dummy'); T.far();`);
  await run(`T.press('${key}')`);
  const seq = await run("T.tick(40, () => [p1.state, p1.t, !!p1.hitbox(), T.fi(p1)])");
  const states = seq.filter(s => s[0] === move).length + 1;
  check(`La Gestora ${move}: lasts exactly ${total} updates then idle`, states === total && seq[total - 1][0] === "idle", `states=${states}`);
  const active = seq.filter(s => s[2]).map(s => s[1]);
  check(`La Gestora ${move}: hitbox only on updates ${a0}-${a1}`, same(active, Array.from({ length: a1 - a0 + 1 }, (_, i) => a0 + i)), JSON.stringify(active));
  check(`La Gestora ${move}: extension frame ${peak} shown while active`, seq.filter(s => s[2]).some(s => s[3] === peak));
  await run(`T.begin('${GR}', 'dummy'); T.near(130); p2.health = 100;`);
  await run(`T.press('${key}')`); await run("T.tick(40)");
  check(`La Gestora ${move}: connects once for ${dmg} damage`, (await run("p2.health")) === 100 - dmg, `hp=${await run("p2.health")}`);
}

// Throw: P1 faces right, opponent far. Sample every update: [state, t, grenades, blasts, gx, gy, bx, by, frame, p2hp, shards]
const SAMPLE = `() => [p1.state, p1.t, grenades.length, blasts.length, grenades[0] ? grenades[0].x : null, grenades[0] ? grenades[0].y : null,
  blasts[0] ? blasts[0].x : null, blasts[0] ? blasts[0].y : null, T.fi(p1), p2.health, particles.filter(p => p.kind === "poop").length]`;
await run(`T.begin('${GR}', 'dummy'); T.far(); p1.facing = 1; T.press('KeyH');`);
const thr = await run(`T.tick(150, ${SAMPLE})`);
const k = thr.findIndex(s => s[2] === 1);                       // first update with a grenade in the air
check("throw: grenade appears on the throwing-pose update (t=34, frame 25) and not before", k > 0 && thr[k][1] === 34 && thr[k][8] === 25 && thr[k - 1][2] === 0, `k=${k} t=${thr[k] && thr[k][1]} frame=${thr[k] && thr[k][8]}`);
check("special: 52 updates long, then idle (not stuck)", thr.findIndex(s => s[0] === "idle") === 51, `idle at ${thr.findIndex(s => s[0] === "idle")}`);
const flight = thr.filter(s => s[2] === 1 && s[4] !== null);
const vx = 11 * Math.cos(40 * Math.PI / 180), g = 0.42;
check("parabola: constant horizontal speed (11 px/update at 40 deg)", flight.length > 40 && flight.slice(1).every((s, i) => Math.abs((s[4] - flight[i][4]) - vx) < 1e-6));
check("parabola: constant gravity (second difference of y = 0.42 px/update^2)", flight.slice(2).every((s, i) => Math.abs((s[5] - 2 * flight[i + 1][5] + flight[i][5]) - g) < 1e-6));
const apex = flight.reduce((m, s, i) => (s[5] < flight[m][5] ? i : m), 0);
check("parabola: rises, peaks, then falls (apex strictly inside the flight)", apex > 0 && apex < flight.length - 1 && flight[0][5] > flight[apex][5] && flight[flight.length - 1][5] > flight[apex][5]);
check("spawn: from the hand (x = 200 + 84 + one update of flight), y = 370 - 11 sin40 + g/2", Math.abs(flight[0][4] - (284 + vx)) < 1e-6 && Math.abs(flight[0][5] - (370 - 11 * Math.sin(40 * Math.PI / 180) + g / 2)) < 1e-6, JSON.stringify(flight[0]));
check("never passes through the floor while in flight", flight.every(s => s[5] < 520));
const landing = thr.find(s => s[3] === 1);
check("explodes exactly once on the floor (blast at y = FLOOR_Y)", thr.filter((s, i) => s[3] === 1 && (i === 0 || thr[i - 1][3] === 0)).length === 1 && landing[7] === 520, JSON.stringify(landing));
check("the grenade is gone after the blast; blast and shards are cleaned up", thr[thr.length - 1][2] === 0 && thr[thr.length - 1][3] === 0 && thr[thr.length - 1][10] === 0);
const shardCount = thr.find(s => s[3] === 1)[10];
check("explosion scatters 9 shards", shardCount === 9, `shards=${shardCount}`);
check("no area damage when the opponent is outside the blast radius", thr[thr.length - 1][9] === 100, `hp=${thr[thr.length - 1][9]}`);

// Facing left mirrors the arc
await run(`T.begin('${GR}', 'dummy'); p1.x = 700; p2.x = 200; p1.facing = -1; T.press('KeyH');`);
const left = await run(`T.tick(40, ${SAMPLE})`);
const li = left.findIndex(s => s[2] === 1), lf = left.filter(s => s[2] === 1);
check("facing left: the grenade starts at 700 - 84 and flies left", li > 0 && Math.abs(lf[0][4] - (616 - vx)) < 1e-6 && lf[1][4] < lf[0][4], JSON.stringify(lf[0]));

// Area of effect: opponent placed in the blast radius -> one hit, exactly 16 damage, and it sticks
const blastX = landing[6];
await run(`T.begin('${GR}', 'dummy'); p1.x = 200; p2.x = ${Math.round(blastX) + 90}; p2.health = 100; T.press('KeyH');`);
const aoe = await run(`T.tick(150, ${SAMPLE})`);
check("area damage: opponent inside the blast radius takes 16 once (power x1.0)", (await run("p2.health")) === 84 && aoe.filter((s, i) => s[3] === 1 && (i === 0 || aoe[i - 1][3] === 0)).length === 1, `hp=${await run("p2.health")}`);
check("area damage: the thrower is never hurt by its own grenade", (await run("p1.health")) === 100);
await run(`T.begin('${GR}', 'dummy'); p1.x = 200; p2.x = 900; T.press('KeyH');`);
const shardVx = await run(`(() => { for (let i = 0; i < 300 && !blasts.length; i++) update();
  return particles.filter(p => p.kind === "poop").map(p => Math.round(p.vx * 100) / 100); })()`);
check("shards: each has its own path (different horizontal speeds, both directions)",
  shardVx.length === 9 && new Set(shardVx).size >= 7 && shardVx.some(v => v < 0) && shardVx.some(v => v > 0), JSON.stringify(shardVx));
check("blast removed after its lifetime", aoe[aoe.length - 1][3] === 0 && aoe[aoe.length - 1][10] === 0);

// Direct hit in mid-air: the opponent stands in the arc -> explodes in the air, still once
await run(`T.begin('${GR}', 'dummy'); p1.x = 200; p2.x = 560; p2.health = 100; T.press('KeyH');`);
const midair = await run(`T.tick(150, ${SAMPLE})`);
const airBlast = midair.find(s => s[3] === 1);
check("direct hit: explodes in mid-air on the opponent (above the floor), 16 damage once", airBlast && airBlast[7] < 520 && (await run("p2.health")) === 84, JSON.stringify(airBlast));

// Cannot be cancelled while the throw animation plays
await run(`T.begin('${GR}', 'dummy'); T.far(); T.press('KeyH'); keys.add('KeyW'); keys.add('KeyF'); keys.add('KeyG'); T.tick(20);`);
check("special: cannot be cancelled into jump/punch/kick", (await run("p1.state === 'special' && p1.y === FLOOR_Y")));
await run("keys.clear()");

// No second grenade while the first is airborne; a new throw is allowed after it lands
await run(`T.begin('${GR}', 'dummy'); T.far(); T.press('KeyH'); T.tick(60);`);
check("one grenade at a time: a new special is ignored while the first is in flight", (await run("grenades.length")) === 1 && (await run("(T.press('KeyH'), p1.state)")) !== "special");
await run("T.tick(120)");
await run("T.press('KeyH')");
check("a new throw is allowed after the previous grenade has exploded", (await run("p1.state")) === "special" && (await run("grenades.length")) === 0);

// screenshots of the grenade in flight and after the blast (debug overlay on: arc, body box, blast radius)
await run(`T.begin('${GR}', 'dummy'); T.far(); p1.facing = 1; T.press('KeyH'); debugBoxes = true; T.tick(45);`);
await shot("gestora-flight");
await run("T.tick(40)"); await shot("gestora-blast");
await run("debugBoxes = false");

// ---- 6. regressions: default fighters, mirror match, clash -------------------------------------------------
await run("T.begin('dummy', 'ministra'); T.far();");
check("default fighter: idle/walk/punch/kick frames unchanged (0, 2, 5, 6)", await run(`(() => {
  const r = []; T.tick(1); r.push(T.fi(p1)); keys.add("KeyD"); T.tick(1); r.push(T.fi(p1)); keys.clear(); T.tick(1);
  T.press("KeyF"); r.push(T.fi(p1)); T.tick(30); T.press("KeyG"); r.push(T.fi(p1)); return JSON.stringify(r) === "[0,2,5,6]"; })()`));
await run("T.begin('dummy', 'ministra'); T.far(); T.press('KeyH'); T.tick(14);");
check("default fighter: Ley de Vivienda still spawns a projectile, hurtbox still 80 wide", (await run("projectiles.length")) === 1 && (await run("p1.hurtbox().w")) === 80);
await run("T.begin('dummy', 'ministra'); T.far(); T.press('KeyW'); T.tick(14); T.press('KeyH'); T.tick(14);");
check("default fighter: air special still works", (await run("projectiles.length")) === 1);
await run("T.begin('rudepolitic', 'rudepolitic');");
check("mirror match: P2 gets a hue shift; hurtbox 120 wide", await run("p2.tint.includes('hue-rotate(180deg)') && p1.tint === 'none' && p1.hurtbox().w === 120"));
await run("T.begin('rudepolitic', 'rudepolitic'); T.near(125);");
check("two Rude Politics cannot overlap (gap = 120)", (await run("T.tick(5); Math.abs(p2.x - p1.x)")) >= 120);
await run("T.begin('rudepolitic', 'dummy'); T.near(115); p1.health = p1.stats.health; p2.health = 100; T.press('KeyF'); T.tick(2); T.press('KeyK'); T.tick(14)");   // both swings first become active on update 9
check("punch vs punch still clashes (no damage)", (await run("p1.health === p1.stats.health && p2.health === 100")));

check("no console errors / exceptions", consoleErrors.length === 0, consoleErrors.join(" | "));
console.log(failures ? `\n${failures} check(s) FAILED` : "\nAll checks passed");
cleanup();
process.exit(failures ? 1 : 0);
