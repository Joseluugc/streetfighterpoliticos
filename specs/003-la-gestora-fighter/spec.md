# Feature Specification: "La Gestora" Playable Fighter & "Gestión de Mierda"

**Feature Branch**: `003-la-gestora-fighter` (no branch created; the work sits on `main` like 002)
**Created**: 2026-11-13
**Status**: Implemented in this change
**Input**: Add a playable female businesswoman fighter from her sprite sheet: dark navy suit, white shirt, formal
trousers, black high heels, brown hair in a ponytail, determined expression. Animations: idle, walk, punch, kick,
jump and the signature special **"Gestión de Mierda"**: she throws a cartoon poop grenade in a parabolic arc, it
explodes on the floor into scattering poop shards and damages opponents inside the blast radius.

## 1. Context (repository analysis findings)

- The playable game is `index.html` (HTML5 canvas, vanilla JS, fixed 60 Hz update). It owns the fighter state
  machine, hit/hurt boxes, paper projectiles, clash rules, particles, the Web-Audio `Sound` module and the
  debug overlay (key `B`). The character select overlay is `ui/character-select/` (`roster.js` + `select.js`).
- Characters are data-driven since spec 002: a JSON definition (`assets/characters/<id>.json` + atlas) declares
  frames, animations, hurtbox, attacks and special. The engine reads only that file (`loadCharacters`,
  `DEFAULT_CHAR` schema in `index.html`).
- The pygame engine in `src/` + `tests/unit/` is not part of the browser game and is left untouched (73 existing
  pytest tests + the new ones keep passing).
- Specials are of three kinds: `projectile` (default fighter's paper), `melee` (Rude Politic's "Golpe Español")
  and, new here, `grenade`.
- The existing Rude Politic atlas builder (`scripts/build_rudepolitic_atlas.py`) was generalised into
  `scripts/build_character_atlas.py` with one layout table per sheet. Its output for Rude Politic is byte-identical
  to the committed files (checked with `git status`).

## 2. Sprite sheet (source of truth)

**Discrepancy**: the brief names `assets/gestionmierda.png`, which does not exist in the repository. The attached
sheet is `assets/characters/bcnfemale.png` (1536x1024, flat gray background `#858585`-ish, labels in dark boxes).
It is used as the source; no other image is substituted.

| Strip | Poses | Source window (x, y) | Used for |
|-------|-------|----------------------|----------|
| MOVIMIENTO | 6 | 0-1536, 55-330 | walk cycle (pose 1 is a stance) |
| PUÑETAZO | 5 | 0-805, 380-640 | idle stance (pose 1), punch |
| PATADA | 5 | 810-1536, 380-640 | kick (pose 1 = stance) |
| SALTO | 5 | 0-810, 640-1000 | takeoff, rise, apex, fall, landing |
| GESTION DE MIERDA | 5 | 810-1412, 695-1000 | special: grab, raise poop, hold overhead, bring forward, throw |
| (flying poop) | 1 | 1412-1536, 740-850 | the grenade sprite (poop, streak and crumbs) |

Findings that shape the design:
- Frame counts are 6/5/5/5/5 plus one projectile sprite, not 9 per animation (see Constitution note in the plan).
- The labels ("MOVIMIENTO", "PUÑETAZO", "PATADA", "SALTO", "GESTION DE MIERDA ...") are blanked before slicing
  and are not rendered.
- The flying poop sits 4 px past the throwing arm; the special strip is cut at x=1412 so the arm and the poop are
  separate pieces. The poop becomes its own sprite and the thrown grenade is drawn by the engine, so the art's
  own flying poop never doubles up with it.
- Poses 3 and 4 of the special touch; they are cut at their emptiest column (same method as Rude Politic).

## 3. User Scenarios & Testing

### US1 - Pick the fighter (P1 or P2)
1. Given the select screen, then a 6th tile "La Gestora" is shown, with portrait cropped from her sheet, bio,
   stat bars and the line "Especial: Gestión de Mierda".
2. Given either player picks her, then in the fight that player is drawn with her sprites and the stat modifiers
   derived from her stats (speed 4 => x1.1, power 3 => x1.0, health 3 => 100 HP). The other fighters are unchanged.

### US2 - Idle, walk, jump
1. Idle alternates the two stance frames (6 and 11) every 30 updates.
2. Walk plays frames 0..5 in order, 6 updates each, in both directions (mirror by facing).
3. Jump: takeoff (first 4 updates), rise, apex; falling shows the fall pose; landing crouch for 6 updates; then idle.
4. Releasing inputs returns to idle; no animation sticks.

### US3 - Punch and kick
1. Punch = 5 frames, 20 updates (startup 6 / active 4 / recovery 10). Hitbox exists only on updates 7-10.
2. Kick = 5 frames, 25 updates (startup 8 / active 5 / recovery 12). Hitbox exists only on updates 9-13.
3. A swing hits at most once. Damage: punch 8, kick 11 (before the power modifier).
4. Punch/kick clash with the opponent's punch/kick exactly as for other fighters (existing rule).

### US4 - "Gestión de Mierda" (signature)
1. Pressing the special key (P1 `H`, P2 `Ñ`/`;`) starts the move on the ground. It cannot be started in the air
   (`airOk: false`), and it cannot be cancelled by the owner's input while it plays.
2. Timeline (52 updates): grab (8) -> raise the poop overhead (10) -> hold overhead (8) -> bring the arm forward (8)
   -> **throw** on the first update of the throwing pose (update 34) -> recovery in the throwing pose (18) -> idle.
3. The poop leaves the throwing hand at update 34, spawned 84 px in front of the feet (never inside the thrower's
   own hurtbox) at the height of the hand.
4. The grenade follows a parabola (see section 4). It explodes **exactly once** on the first of:
   a. it reaches the floor (`y >= FLOOR_Y`), at the floor under its current x; or
   b. it touches an opponent's hurtbox in mid-air (direct hit), at that point.
5. The blast is an area-of-effect hit: every opponent whose hurtbox lies within the blast radius takes damage once
   (16 x the owner's damage modifier), is pushed away from the blast, and enters hit-stun. The thrower is never hurt.
6. The blast produces: a central flash and sparks, a dust burst, a ground-level shockwave ring that expands to the
   blast radius and fades, 9 poop shards that scatter with their own velocities and gravity and bounce once on the
   floor, a boom sound and camera shake (>= 18). A banner "¡GESTIÓN DE MIERDA!" appears above the fighter.
7. Only one grenade per fighter may be in flight: while it is airborne the special is ignored. After it explodes
   the fighter can throw again.
8. The special is not clashable by punches/kicks (a grenade is not an attack box) and is not a paper projectile:
   papers still clash with papers only.

### Edge cases
- Special pressed while the previous grenade is still in flight, while stunned, or after the round is over -> ignored.
- Opponent right next to the thrower: the grenade spawns clear of the thrower's own body, but may overlap the
  opponent and detonate at point-blank range; the thrower is still not hurt.
- Opponent outside the radius: the grenade still explodes on the floor (no damage, shards and ring still play).
- Opponent in the blast with the arc passing through its hurtbox: it detonates at the first contact; still one hit.
- Round reset (`R`) or returning to select (`Esc`): all grenades, blasts and shards are cleared.
- Sheet or JSON missing or invalid: the fighter is left out of the roster with a console warning; the other
  fighters keep working (existing 002 behaviour).
- Opening `index.html` from `file://`: the JSON fetch fails and the fighter is omitted (serve the folder).

## 4. Grenade physics (normative)

- Time is counted in simulation updates (1/60 s each), never wall-clock time or render frames (constitution IV).
- Launch velocity from the configured speed and angle: `vx = facing · speed · cos(angle)`, `vy = -speed · sin(angle)`
  (y grows downwards, so `vy < 0` is upward).
- Position after `n` updates in flight, exactly:
  `x(n) = x0 + vx · n`,  `y(n) = y0 + vy · n + ½ · g · n²`.
  `g` is the configured `gravity` (px per update²). The engine evaluates these formulas each update, so no drift
  accumulates and the arc is identical at any frame rate.
- Facing left mirrors `vx` (and the spawn side); the sprite is mirrored and tilted along the arc, with the streak
  always trailing behind.
- Ground: as soon as `y >= FLOOR_Y` the grenade detonates at `FLOOR_Y`. It never rests below the floor.
- Debug overlay (`B`): the grenade body box, the predicted arc to the floor (dotted yellow), and the blast radius
  (magenta circle) for each live blast.

## 5. Configuration (data, not code)

All values live in `assets/characters/gestora.json`:
- `special.grenade`: `speed` 11, `angle` 40, `gravity` 0.42, `box` 40x40, `spawn` (x 84, y -150), `damage` 16,
  `push` 24, `blastRadius` 120, `blastLife` 22, `frame` 26 (the flying poop sprite).
- `special.grenade.shards`: `count` 9, `speed` 6, `gravity` 0.3, `life` 36, `scale` 0.22.
- `special.launch`: 34 (update of the throw); `special.airOk`: false; `special.kind`: `"grenade"`.
- `hurt` 96x205; `attacks.punch` / `attacks.kick` as in section 3; `scale` 0.9.

## 6. Functional Requirements

- **FR-1** Definition `assets/characters/gestora.json` + atlas `assets/characters/gestora.png` generated by
  `scripts/build_character_atlas.py gestora` from `assets/characters/bcnfemale.png`. Transparent background, no labels,
  no neighbour bleed, interior gray highlights preserved, pixels unscaled.
- **FR-2** Roster entry `id: gestora`, name "La Gestora", stats 4/3/3, `special: "Gestión de Mierda"`.
- **FR-3** The engine reads only the definition; `kind: "grenade"` is a new special kind next to `projectile` and `melee`.
- **FR-4** Animation frame is a pure function of state and tick (existing `animFrame` logic, unchanged).
- **FR-5** The grenade is integrated in `updateGrenades()` each update, detonates once, and is removed at detonation.
  Blasts and shards are removed when their lifetimes end.
- **FR-6** Damage goes through `takeHit()` (existing combat system) with the owner's `stats.damage`.
- **FR-7** Default fighters and Rude Politic keep identical behaviour; their tests are unchanged.

## 7. Success Criteria (measurable)

- **SC-1** Atlas: 27 frames inside the atlas, none overlapping, every frame has >=10% opaque pixels, the atlas
  corners are transparent, and under 4% of each frame's opaque pixels are the sheet's gray.
- **SC-2** Throw sync: the grenade appears on update 34, when the special frame is 25 (throwing pose), and not before.
- **SC-3** Parabola: horizontal step is constant (11·cos40° px/update) and the second difference of `y` is
  constant (0.42 px/update²) across the whole flight, verified in the running game (tolerance 1e-6).
- **SC-4** Spawn: first sampled position is `(feet_x + 84 + vx, 370 - 11·sin40° + g/2)` for facing right.
- **SC-5** Ground: the flight never goes below `y = 520`; the single blast occurs at `y = 520`; the grenade is gone
  afterwards; 9 shards exist at detonation and are cleaned up after their lifetime; the blast ring is removed.
- **SC-6** Area damage: an opponent inside the radius takes exactly 16 damage once; one outside takes none; the
  thrower takes none; a mid-air direct hit explodes above the floor, once.
- **SC-7** Special length 52 updates and ends in `idle`; cannot be cancelled; only one grenade in flight per fighter;
  a new throw is allowed after the explosion.
- **SC-8** Punch 20 updates (hitbox 7-10), kick 25 (hitbox 9-13), with damage 8 and 11.
- **SC-9** Full pytest suite passes (82 tests) and the headless browser smoke test passes with no console errors.

## 8. Out of Scope
- Guard/defend animation (no sheet frames; the browser game has no block state).
- Extra throw frames or a separate shard sprite (the 5 poses and the flying poop are all the sheet has; shards are
  scaled copies of the flying poop, streak included).
- Air grenades (`airOk` is false by design; the code path exists in data).
- Changes to the pygame engine in `src/`.
- Committing or pushing: the new files are left as working-tree changes for review.
