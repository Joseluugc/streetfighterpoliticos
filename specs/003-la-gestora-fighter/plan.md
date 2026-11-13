# Implementation Plan: "La Gestora" Fighter & "Gestión de Mierda"

**Spec**: `specs/003-la-gestora-fighter/spec.md`

## Technical context
HTML5 canvas + vanilla JS (`index.html`, `ui/character-select/`), fixed 60 Hz update. Asset tooling in Python/pygame
(`scripts/`), tests in pytest (`tests/unit/`) and a headless Chrome smoke test (`tests/e2e/browser_smoke.mjs`).
No new dependencies.

## Repository findings that drive the design
- The data-driven character pipeline from spec 002 already exists (`loadCharacters`, `CHAR_DEFS`, `animFrame`,
  per-character `hurt` / `attacks` / `special`). A new fighter therefore needs a definition, an atlas and a roster entry.
- Specials already branch on `special.kind` (`projectile`, `melee`). A third kind, `grenade`, follows the same pattern.
- The paper `Projectile` moves in a straight line (`vx` only). It is left as it is; the grenade is a separate class,
  because a parabola needs `vy` and gravity, and the paper's clash and direct-hit rules do not apply to it.
- The square-root-free analytic arc `x0 + vx·n`, `y0 + vy·n + ½·g·n²` is exact in simulation updates. Constitution
  IV requires gameplay timing in frames, so updates replace the brief's "delta time" (the loop is fixed-step).

## Design decisions
1. **`kind: "grenade"` special, data-driven.** Launch frame, grenade parameters, shard parameters and sprite frame all
   live in the definition. Code only reads them. *Alternative rejected:* a new state for the grenade. The grenade is
   an entity, not a fighter state, so it is a list in the game (`grenades`), like `projectiles`.
2. **Analytic ballistics in updates.** `Grenade.pointAt(n)` is pure; `advance()` sets `x,y` from `n`. No accumulated
   error, frame-rate independent, and the debug overlay draws the same function for the predicted arc.
3. **Spawn at the throwing pose.** The throw happens on the first update of the throwing pose (`launch = 34`),
   so the animation and the projectile are in sync by construction. A test checks `launch == sum(ticks[:4])`.
4. **Single detonation.** `detonate()` marks the grenade dead before it applies damage. The grenade list is filtered
   after each step, so a dead grenade can't detonate twice. Damage goes through `takeHit` with the owner's modifier.
5. **Area of effect = circle vs hurtbox rectangle** (`circleHitsBox`): nearest point of the box inside the radius.
   It works for airborne opponents and the owner is excluded.
6. **Shards reuse the particle system.** A `poop` particle kind carries its own sprite reference, velocity, gravity,
   rotation and lifetime; the existing `updateParticles` integrates and cleans them up. One bounce on the floor is
   added for this kind only, so other particles are unchanged.
7. **Shockwave = a `blasts` list** (position, radius, life). It is drawn as an expanding ring and, in the debug
   overlay, as the blast radius. It is removed when its lifetime ends.
8. **Atlas builder generalised, not copied.** `scripts/build_character_atlas.py` holds one `Sheet` entry per character
   (source, outputs, strip windows, label boxes). A strip with count 1 is one sprite made of every piece in its
   window, which is how the flying poop is extracted. Rude Politic regenerates byte-identically.
9. **Throw sprite and shards are cut from the sheet** (the flying poop, streak included), not drawn procedurally, so
   the art stays in the sheet's style. The spec documents this.

## Constitution Check
| Principle | Status | Notes |
|---|---|---|
| I. OO design & separation | ✅ | `Grenade` owns its physics; drawing is `drawGrenade`/`drawParticles`; input untouched. Global detonation helpers follow the `slamImpact` precedent from spec 002. |
| II. FSM for character behaviour | ✅ with precedent | `special` state with `kind: "grenade"`; uninterruptible; ends in `idle`. The browser game uses string states (spec 002 precedent), not an enum. |
| III. Hitbox / hurtbox separation | ✅ | The grenade body box is a *projectile* box, not an attack hitbox. Area damage tests the opponent's hurtbox only. Exactly one detonation per grenade (one hit per instance). Debug overlay shows body, arc and radius. |
| IV. Fixed-timestep loop | ✅ | All motion in updates; no wall-clock time; deterministic given the inputs. The brief's "delta time" is replaced by the fixed step, as the constitution requires. |
| V. Spritesheet slicing (9 frames) | ⚠ deviation | The sheet has 6/5/5/5/5 poses plus one projectile sprite. Recorded in Complexity Tracking. |

## Complexity Tracking
- **Principle V (9 frames per animation)**: not met. The supplied art has 6 walk, 5 punch, 5 kick, 5 jump and 5 special
  poses, plus the flying poop. Padding to 9 would mean inventing poses, which the brief forbids. The browser game's
  frame data is per character (spec 002, FR-1, `frames`/`animations` in JSON), and load-time validation fails only on
  missing or invalid files. The 9-frame rule was written for the pygame engine in `src/`, which is not changed.
- **Browser game tested in a headless browser, not pytest**: the game logic lives in `index.html` (JS). It is
  covered by `tests/e2e/browser_smoke.mjs` (Chrome over CDP), as in spec 002. The pytest suite covers the data and
  the atlas (`tests/unit/test_gestora_atlas.py`), including the throw/animation sync and arc sanity.
- **Global detonation helpers rather than a class per effect**: `detonate()` and `updateGrenades()` are global,
  as `slamImpact()` is in spec 002. They are small and used only by the grenade.

## Files
| Action | File | Purpose |
|---|---|---|
| rename + generalise | `scripts/build_rudepolitic_atlas.py` -> `scripts/build_character_atlas.py` | one builder, layout table per sheet |
| create | `assets/characters/gestora.png` | transparent atlas, 27 frames (generated) |
| create | `assets/characters/gestora.json` | definition: frames, strips, animations, hurt, attacks, grenade special |
| modify | `assets/characters/rudepolitic.json` | `source` note points at the new builder (atlas unchanged) |
| modify | `index.html` | `Grenade` class, `detonate`/`updateGrenades`/`circleHitsBox`, `drawGrenade`, `throwGrenade`, grenade branch in the special state, `poop` particles, blast ring, debug overlay |
| modify | `ui/character-select/roster.js` | 6th roster entry |
| modify | `tests/e2e/browser_smoke.mjs` | roster 6, select 6 tiles, La Gestora section (basics, punch/kick, throw, parabola, floor, AoE, direct hit, cancels, one grenade), screenshots |
| create | `tests/unit/test_gestora_atlas.py` | atlas, timing, throw sync and arc sanity |
| create | `specs/003-la-gestora-fighter/{spec,plan,tasks}.md` | this feature |
| untracked (not committed) | `assets/characters/bcnfemale.png` | the supplied source sheet, used by the builder |

## Testing strategy
- **pytest** (headless, `SDL_VIDEODRIVER` not needed for the checks): atlas layout, transparency, gray removal,
  anchors, animation references, attack/special timing, throw sync (`launch`), arc configuration sanity.
- **Headless Chrome** (`node tests/e2e/browser_smoke.mjs`): drives the real page through the test hook `T`.
  Asserts state/frame/hitbox windows, damage numbers, the parabola (constant `vx`, constant second difference of `y`),
  the floor detonation, area damage exactly once, shard count and cleanup, mid-air direct hit, facing, cancels and
  one-grenade-at-a-time. Saves screenshots of the arc and the blast when `SHOTS=<dir>` is set.
- **Regressions**: the 73 original pytest tests, Rude Politic atlas regenerates byte-identically, default fighters'
  frame choice and projectile unchanged (existing smoke sections).
