# Feature Specification: "Rude Politic" Playable Fighter & "Golpe Español"

**Feature Branch**: `002-rude-politic-fighter`
**Created**: 2026-11-11
**Status**: Approved (implemented in this change)
**Input**: Add a new playable character built from `assets/rudepolitic.png`: a huge, muscular, hairy man in
a navy business suit (white shirt, red tie, thick beard, messy dark-brown hair). Animations: idle, movement,
punch, kick, jump and the signature special **"Golpe Español"** (a Spanish-flag overhead slam).

## 1. Context (repository analysis findings)

- The **playable game is `index.html`** (HTML5 canvas, vanilla JS, 60 Hz fixed timestep). It owns the fighter
  FSM (`idle/walk/jump/fall/punch/kick/special/hit`), hit/hurt boxes, projectiles, clash rules, particles and the
  Web-Audio `Sound` module. The character-select overlay lives in `ui/character-select/` (`roster.js` + `select.js`).
- `src/` + `tests/` is the earlier pygame engine (65 passing pytest tests). It does not contain the select screen,
  clash rules or air special; it is **left untouched** and must keep passing.
- Until now every fighter used one hard-coded sheet (`FRAMES`, `ATTACKS`, `SPECIAL`, `HURT`, `SCALE` globals in
  `index.html`); the roster only varied tint and stats. This feature therefore also introduces a small
  **per-character definition** so a fighter can bring its own sheet, frame timings, hitboxes and special.
- Input is already abstracted per fighter through `controls` (P1 `WASD/F/G/H`, P2 arrows `K/L/Ñ`).

## 2. Sprite sheet analysis (`assets/rudepolitic.png`, 1536x1024, flat gray background)

| Strip | Poses | Source window (x, y) | Pose size (px) | Used for |
|-------|-------|----------------------|----------------|----------|
| MOVIMIENTO | 6 | 0-1536, 55-330 | ~190-211 x 215-231 | walk cycle |
| PUÑETAZO | 5 | 0-805, 380-640 | 142-200 x 201-213 | idle stance (pose 1), punch |
| PATADA | 5 | 810-1536, 380-640 | 105-173 x 210-215 | kick (pose 1 = stance) |
| SALTO | 5 | 0-810, 640-1000 | 122-173 x 181-213 | takeoff, rise, apex, fall, landing |
| GOLPE ESPAÑOL | 5 | 810-1536, 695-1000 | 140-193 x 153-273 | special |

Findings that shape the design:
- Labels ("MOVIMIENTO" ...) are dark boxes and must never be rendered.
- Poses touch (punch 3/4) or overlap bounding rectangles (jump 4/5), so cropping by rectangle leaks neighbours.
- Gray-ish highlights *inside* the suit are within colour-key tolerance and would become holes.
- The brief mentions 12 special frames; **the supplied sheet contains 5**. The special is built from those 5 with
  per-frame hold times plus procedural motion/impact effects (see FR-9).

## 3. User Scenarios & Testing

### US1 - Pick the fighter (P1)
**Acceptance**
1. Given the select screen, then a 5th tile "Rude Politic" is shown with portrait (cropped from its own sheet),
   bio, stat bars and a line "Especial: Golpe Español".
2. Given either player picks it, then in the fight that player is drawn with the new sprites (no tint) and
   gameplay modifiers derived from its stats. The other fighters are unchanged.
3. Given both players pick it, then P2 is hue-shifted so they can be told apart.

### US2 - Idle, walk, jump (P1)
1. Idle alternates two stance frames every 30 updates.
2. Walk plays the 6 movement frames in order, 6 updates each (36-update cycle), in both directions (sprite mirrors).
3. Jump shows takeoff (first 4 updates), rising, apex pose; falling shows the fall pose; on landing a landing-crouch
   pose is shown for 6 updates without blocking input.
4. Releasing inputs returns to idle; no animation sticks.

### US3 - Punch and kick (P1)
1. Punch = 5 frames, 24 updates (startup 7 / active 4 / recovery 13). Hitbox exists only in the active window.
2. Kick = 5 frames, 28 updates (startup 9 / active 5 / recovery 14). Hitbox exists only in the active window.
3. One swing hits at most once. Holding the key repeats the move only after it has fully finished.
4. Punch/kick clash with the opponent's punch/kick exactly as for other fighters (existing rule).
5. Ends in idle (or walk if a direction is held).

### US4 - "Golpe Español" (P1 - signature)
1. Pressing the special key starts the move on the ground **or in the air** (jump/fall). In the air the fighter keeps
   falling with gravity and jump momentum while the move plays, lands normally, and ends in `fall` (still airborne) or `idle`.
2. Timeline (52 updates): grab/raise flag (8) -> hold above head (10) -> swing begins (8) -> **impact**
   (8, hitbox active updates 27-30) -> recovery with flag on the floor (18) -> idle.
3. At the impact update: ground burst in red/yellow/dust, camera shake >= 18, boom sound, and a motion-trail
   (ghost of the raised pose) during the downward swing. A banner "¡GOLPE ESPAÑOL!" appears above the fighter.
4. Damage = 22 x power modifier (clearly above kick 11 and punch 8), knockback 34; the hitbox covers the
   area in front of the fighter from head height to the floor (reaches airborne opponents too).
5. It cannot be cancelled by the owner's own input. It is interrupted only by taking a hit (same as every state).
6. It is not a projectile (no paper spawns) and is **not clashable** by punches/kicks (they trade damage instead).
7. The name "Golpe Español" appears in: roster panel, in-fight banner, voice shout. (Dummy-style fighters keep
   "Ley de Vivienda".)

### Edge cases
- Special pressed while a previous special is active, hit-stunned, or after the round is over -> ignored.
- Fighter KO'd mid-special: stays in the special pose until reset; no further hitbox is created after health 0 ends the round.
- Sheet / JSON missing or invalid: the character is omitted from the roster with a console warning; the other 4
  fighters keep working.
- Screen edges: fighter x is clamped using the character's own hurtbox width.
- Opening `index.html` from `file://`: fetch of the JSON fails -> character omitted (documented: serve the folder).

## 4. Functional Requirements

- **FR-1** A character definition file `assets/characters/rudepolitic.json` (+ atlas `rudepolitic.png`) declares sheet,
  scale, frames, animations, hurtbox, attacks and special. The engine reads **only** this definition.
- **FR-2** The atlas is generated by `scripts/build_rudepolitic_atlas.py` from `assets/rudepolitic.png`: transparent
  background, no labels, no neighbour bleed, interior gray highlights preserved, original pixels unscaled.
- **FR-3** Fighters carry a `char` (definition); frames, boxes, scale, hurtbox and specials come from it. The
  original fighters keep identical behaviour through a built-in default definition.
- **FR-4** Animation frame is derived from `(state, t, vy, landTimer)` only (never stored separately).
- **FR-5** Walk speed, damage and max health use the existing stat-modifier mechanism (speed 2, power 5, health 4
  => x0.9 speed, x1.2 damage, 110 HP).
- **FR-6** Hurtbox 120x205; punch box 85x55 at (+40,-165); kick box 100x70 at (+45,-160); special box 170x170 at (+20,-170).
- **FR-7** Special is a melee state with `clash: false`, `airOk: true`, hit once (`hitDone`).
- **FR-8** Sprites keep a hip anchor so the body does not slide between poses; feet sit on the floor line.
- **FR-9** Visual feedback: trail during swing, impact particles, shake, banner; no feedback if frames are missing.
- **FR-10** Roster entry (`id: rudepolitic`) exposes `special: "Golpe Español"`; the panel shows it.

## 5. Success Criteria (measurable)

- **SC-1** Atlas: 26 frames, all inside the atlas, none overlapping each other, every frame has >=15% opaque
  pixels, the 4 corner pixels of the atlas are transparent, and no pixel of any frame equals the sheet's gray.
- **SC-2** Walk cycle advances frame index every 6 updates and wraps 0..5.
- **SC-3** Punch hitbox active on exactly updates 8-11; kick 10-14; special 27-30; none outside.
- **SC-4** Special total length is 52 updates and ends in `idle`.
- **SC-5** Existing 65 pytest tests still pass; the other four fighters' frame choice is unchanged.
- **SC-6** Headless browser run: P1 as Rude Politic performs walk, jump, punch, kick, special against P2 with no
  console errors, and P2 loses exactly the expected damage (22 x 1.2 = 26 for a clean Golpe Español).

## 6. Out of Scope
- Guard/defend animation (no sheet frames; the browser game has no block state).
- 12-frame special (only 5 frames supplied); extra frames would be hand-drawn art.
- Changes to the pygame engine in `src/`.
