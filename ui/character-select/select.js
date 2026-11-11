/**
 * CharacterSelect: a self-contained, two-player character selection screen (DOM overlay).
 *
 *   CharacterSelect.init({
 *     root,                      // element the screen is rendered into
 *     roster,                    // array from roster.js
 *     getSprite(idleIdx, ch),    // -> { img, rect:{x,y,w,h} } : idle frame (0/1) of that character's keyed sheet
 *     sound,                     // optional { move(), select(), cancel(), ready(), start() } (all optional)
 *     onStart({ p1, p2 })        // called once both players locked in; receives the two roster entries
 *   });
 *   CharacterSelect.show();  CharacterSelect.hide();  CharacterSelect.active  // -> boolean
 *   CharacterSelect.statsToMods(stats) // -> { speed, damage, health } gameplay multipliers
 *
 * No dependency on the game: it only talks to the outside world through the callbacks above.
 */
(function (global) {
  "use strict";

  const COLS = 2;                       // grid columns (keep in sync with select.css)
  const AUTO_START_MS = 1400;           // delay between "both ready" and the fight starting
  const TILE_SIZE = 168, PREVIEW_W = 280, PREVIEW_H = 308;   // canvas backing-store sizes (CSS scales them)

  /** Per-player cursor keys. confirm/cancel are lists of KeyboardEvent.code values. */
  const PLAYERS = [
    { label: "JUGADOR 1", keys: { left: "KeyA", right: "KeyD", up: "KeyW", down: "KeyS", confirm: ["KeyF"], cancel: ["KeyG"] } },
    { label: "JUGADOR 2", keys: { left: "ArrowLeft", right: "ArrowRight", up: "ArrowUp", down: "ArrowDown", confirm: ["KeyK"], cancel: ["KeyL"] } },
  ];

  /** Convert the 1-5 display stats to gameplay modifiers. 3 = the original numbers (x1.0 / 100 HP). */
  function statsToMods(s) {
    return { speed: 1 + (s.speed - 3) * 0.1, damage: 1 + (s.power - 3) * 0.1, health: 100 + (s.health - 3) * 10 };
  }

  let opts, roster, root, els = {}, open = false, animTimer = null, startTimer = null, idleFrame = 0;
  const portraitImgs = {};              // id -> loaded <img> for roster entries that define `portrait`
  const state = PLAYERS.map(() => ({ idx: 0, ready: false }));
  state[1].idx = 1;                     // P2 starts on the second fighter so cursors don't overlap

  const sfx = name => { try { opts.sound && opts.sound[name] && opts.sound[name](); } catch (e) { /* audio is optional */ } };
  const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };

  // ---- drawing --------------------------------------------------------------------------------
  /** Draw a character into a canvas. `headOnly` crops the sprite to head+torso (roster tiles). */
  function drawChar(canvas, ch, { frame = 0, headOnly = false, bob = 0 } = {}) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = false;
    const custom = portraitImgs[ch.id];
    let img, r;
    if (custom) { img = custom; r = { x: 0, y: 0, w: custom.naturalWidth, h: custom.naturalHeight }; }
    else {
      const s = opts.getSprite(frame, ch); if (!s) return;
      img = s.img; r = { ...s.rect };
      if (headOnly) r.h = Math.round(r.h * 0.5);
    }
    const pad = headOnly ? 6 : 10;
    const k = Math.min((canvas.width - pad * 2) / r.w, (canvas.height - pad * 2) / r.h);
    const w = r.w * k, h = r.h * k;
    ctx.save();
    if (!custom && ch.tint && ch.tint !== "none") ctx.filter = ch.tint;
    ctx.drawImage(img, r.x, r.y, r.w, r.h, (canvas.width - w) / 2, canvas.height - pad - h + bob, w, h);
    ctx.restore();
  }

  function drawAll() {
    roster.forEach((ch, i) => drawChar(els.tiles[i].canvas, ch, { headOnly: true }));
    drawPreviews();
  }
  function drawPreviews() {
    state.forEach((st, p) => drawChar(els.panels[p].canvas, roster[st.idx], { frame: idleFrame, bob: idleFrame ? -2 : 0 }));
  }

  // ---- DOM ------------------------------------------------------------------------------------
  function build() {
    root.innerHTML = "";
    const cs = el("div", "cs"); cs.setAttribute("role", "dialog"); cs.setAttribute("aria-label", "Selección de personaje");
    cs.appendChild(el("h1", "cs__title", "ELIGE A TU LUCHADOR"));

    const main = el("div", "cs__main");
    els.panels = [panel(0), null];
    main.appendChild(els.panels[0].node);

    const grid = el("ul", "cs__grid"); grid.setAttribute("role", "listbox");
    els.tiles = roster.map((ch, i) => {
      const li = el("li", "cs__tile"); li.setAttribute("role", "option"); li.title = ch.name;
      const canvas = el("canvas"); canvas.width = canvas.height = TILE_SIZE;
      li.append(canvas, el("span", "cs__tile-name", ch.name));
      const tag1 = el("span", "cs__tag cs__tag--p1", "P1"), tag2 = el("span", "cs__tag cs__tag--p2", "P2");
      li.append(tag1, tag2); tag1.hidden = tag2.hidden = true;
      // Mouse: hovering moves the cursor of the first player who hasn't locked in; click confirms.
      li.addEventListener("pointerenter", () => { const p = mousePlayer(); if (p >= 0) moveTo(p, i); });
      li.addEventListener("click", () => { const p = mousePlayer(); if (p >= 0) { moveTo(p, i, true); confirm(p); } });
      grid.appendChild(li);
      return { node: li, canvas, tags: [tag1, tag2] };
    });
    main.appendChild(grid);
    els.panels[1] = panel(1);
    main.appendChild(els.panels[1].node);
    cs.appendChild(main);

    els.status = el("div", "cs__status");
    els.fight = el("button", "cs__fight", "¡LUCHAR!"); els.fight.type = "button"; els.fight.disabled = true;
    els.fight.addEventListener("click", startFight);
    cs.append(els.status, els.fight, el("p", "cs__hint",
      "<b>J1</b> <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> mover · <kbd>F</kbd> elegir · <kbd>G</kbd> cancelar &nbsp;|&nbsp; " +
      "<b>J2</b> <kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd> mover · <kbd>K</kbd> elegir · <kbd>L</kbd> cancelar<br>También con el ratón: pasa por encima y haz clic"));
    root.appendChild(cs);
    els.cs = cs;
  }

  function panel(p) {
    const node = el("section", "cs__panel"); node.dataset.player = p;
    const canvas = el("canvas", "cs__preview"); canvas.width = PREVIEW_W; canvas.height = PREVIEW_H;
    const name = el("h2", "cs__name"), epithet = el("p", "cs__epithet"), bio = el("p", "cs__bio"), special = el("p", "cs__special");
    const stats = el("div", "cs__stats"), bars = {};
    [["speed", "VELOCIDAD"], ["power", "FUERZA"], ["health", "VIDA"]].forEach(([k, label]) => {
      const bar = el("div", "cs__bar"), fill = el("i"); bar.appendChild(fill);
      stats.append(el("span", null, label), bar); bars[k] = fill;
    });
    const badge = el("div", "cs__badge");
    node.append(el("div", "cs__who", PLAYERS[p].label), canvas, name, epithet, bio, special, stats, badge);
    return { node, canvas, name, epithet, bio, special, bars, badge };
  }

  /** Sync the whole UI to `state`. `changedPlayer` (optional) re-triggers that panel's swap animation. */
  function refresh(changedPlayer) {
    els.tiles.forEach((t, i) => {
      PLAYERS.forEach((_, p) => {
        const here = state[p].idx === i;
        t.node.classList.toggle(`is-p${p + 1}`, here);
        t.tags[p].hidden = !here;
        t.tags[p].classList.toggle("is-ready", here && state[p].ready);
      });
      t.node.setAttribute("aria-selected", state.some(s => s.idx === i));
    });
    state.forEach((st, p) => {
      const ch = roster[st.idx], pn = els.panels[p];
      pn.name.textContent = ch.name; pn.epithet.textContent = ch.title; pn.bio.textContent = ch.bio;
      pn.special.innerHTML = ch.special ? "ESPECIAL: <b></b>" : ""; if (ch.special) pn.special.firstElementChild.textContent = ch.special;
      for (const k in pn.bars) pn.bars[k].style.width = (ch.stats[k] / 5 * 100) + "%";
      pn.badge.textContent = st.ready ? "¡LISTO!" : "ELIGIENDO…";
      pn.node.classList.toggle("is-ready", st.ready);
      if (p === changedPlayer) { pn.node.classList.remove("is-swap"); void pn.node.offsetWidth; pn.node.classList.add("is-swap"); }
    });
    const all = state.every(s => s.ready);
    els.fight.disabled = !all;
    els.status.textContent = all ? "¡Preparados! La pelea empieza…"
      : state[0].ready ? "Esperando al Jugador 2…" : state[1].ready ? "Esperando al Jugador 1…" : "";
    drawPreviews();
  }

  // ---- interaction ----------------------------------------------------------------------------
  const mousePlayer = () => state.findIndex(s => !s.ready);   // who the mouse currently controls

  function moveTo(p, idx, silent) {
    if (state[p].ready || state[p].idx === idx) return;
    state[p].idx = idx; if (!silent) sfx("move");
    refresh(p);
  }
  function move(p, dx, dy) {
    if (state[p].ready) return;
    const n = roster.length;
    const idx = dy ? state[p].idx + dy * COLS : state[p].idx + dx;
    moveTo(p, ((idx % n) + n) % n);
  }
  function confirm(p) {
    if (state[p].ready) return;
    state[p].ready = true;
    els.tiles[state[p].idx].node.classList.remove("is-locked"); void els.tiles[state[p].idx].node.offsetWidth;
    els.tiles[state[p].idx].node.classList.add("is-locked");
    sfx("select"); refresh();
    if (state.every(s => s.ready)) { sfx("ready"); clearTimeout(startTimer); startTimer = setTimeout(startFight, AUTO_START_MS); }
  }
  function cancel(p) {
    if (!state[p].ready) return;
    state[p].ready = false; clearTimeout(startTimer); startTimer = null;
    sfx("cancel"); refresh();
  }
  function startFight() {
    if (!open || !state.every(s => s.ready)) return;
    clearTimeout(startTimer); startTimer = null;
    sfx("start");
    opts.onStart({ p1: roster[state[0].idx], p2: roster[state[1].idx] });
  }

  function onKey(e) {
    if (!open || e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
    for (let p = 0; p < PLAYERS.length; p++) {
      const k = PLAYERS[p].keys;
      if (e.code === k.left)  { move(p, -1, 0); e.preventDefault(); return; }
      if (e.code === k.right) { move(p, 1, 0);  e.preventDefault(); return; }
      if (e.code === k.up)    { move(p, 0, -1); e.preventDefault(); return; }
      if (e.code === k.down)  { move(p, 0, 1);  e.preventDefault(); return; }
      if (k.confirm.includes(e.code)) { confirm(p); e.preventDefault(); return; }
      if (k.cancel.includes(e.code))  { cancel(p);  e.preventDefault(); return; }
    }
  }

  // ---- public API -----------------------------------------------------------------------------
  global.CharacterSelect = {
    statsToMods,
    get active() { return open; },
    init(options) {
      opts = options; roster = options.roster; root = options.root;
      build();
      roster.forEach(ch => {                              // optional hand-made portraits override the sprite crop
        if (!ch.portrait) return;
        const img = new Image();
        img.onload = () => { portraitImgs[ch.id] = img; if (open) drawAll(); };
        img.src = ch.portrait;                            // a missing file simply keeps the sprite crop
      });
      addEventListener("keydown", onKey, true);           // capture: runs before the game's own key handler
    },
    show() {
      state.forEach(s => { s.ready = false; });
      open = true; els.cs.classList.add("is-open");
      refresh(); drawAll();
      clearInterval(animTimer);
      animTimer = setInterval(() => { idleFrame ^= 1; drawPreviews(); }, 450);   // idle A / idle B breathing
    },
    hide() {
      open = false; els.cs.classList.remove("is-open");
      clearInterval(animTimer); clearTimeout(startTimer); startTimer = null;
    },
  };
})(window);
