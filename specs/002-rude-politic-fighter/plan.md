# Implementation Plan: "Rude Politic" Fighter & "Golpe Español"

**Spec**: `specs/002-rude-politic-fighter/spec.md`

## Technical context
HTML5 canvas + vanilla JS (single `index.html` game, `ui/character-select/` overlay), 60 Hz fixed step.
Asset tooling in Python/pygame (`scripts/`), tests in pytest (`tests/`). No new dependencies.

## Design decisions
1. **Per-character definition, default preserved.** `DEFAULT_CHAR` is assembled in `index.html` from the existing
   `FRAMES/ATTACKS/SPECIAL/HURT/SCALE` constants, so the four existing fighters behave identically. New characters
   come from a JSON file referenced by the roster entry (`sprite`). *Alternative rejected:* more globals / `if (id === ...)`.
2. **Pre-keyed atlas instead of colour-keying at runtime.** A build script cuts each pose by its own pixels and
   writes a transparent PNG; the JSON carries `"keyed": true`, so the runtime colour-key (which would delete the
   black shoes if applied to a transparent corner) is skipped. Works on `file://` for images; only the JSON `fetch` needs a server.
3. **Animation is a pure function of state.** Anim spec = `{frames, tick}` (loop) or `{frames, ticks[]}` (one-shot);
   `animFrame(fighter)` also handles jump sub-phases (takeoff / rise / apex) from `t` and `vy`, and landing from `landT`.
4. **Special as `kind: "melee"`.** Reuses the attack-table path (`hitbox()`, `resolveHit()`); only the state's
   update branch, the impact effect and clash opt-out are new. Projectile specials stay as they are.
5. **Hip anchor** (median x of dark pixels in rows 50-90 %) rather than head centre: heads move a lot in these poses; hips don't.
6. **Select screen** asks the game for a portrait frame per character (`getSprite(frame, ch)`).

## Files
| Action | File | Purpose |
|---|---|---|
| create | `scripts/build_rudepolitic_atlas.py` | slice sheet -> atlas + frames JSON |
| create | `assets/characters/rudepolitic.png` / `.json` | atlas + definition (animations, boxes, special) |
| modify | `index.html` | `DEFAULT_CHAR`, definition loader, `animFrame`, per-char hurt/attacks/special, slam impact, trail, banner, `Sound.slam` |
| modify | `ui/character-select/roster.js` | 5th roster entry, `special` name |
| modify | `ui/character-select/select.js` | per-character portrait frame, special line, 3-row grid |
| modify | `ui/character-select/select.css` | special line style |
| create | `tests/unit/test_rudepolitic_atlas.py` | atlas + definition validation (SC-1..SC-4) |
| create | `tests/e2e/browser_smoke.py` (script) | headless Chrome playthrough (SC-6) |
| delete | `scripts/measure_rudepolitic.py` | superseded by the builder (never committed) |

## Testing strategy
- pytest (headless): atlas/definition invariants; timing arithmetic (startup+active+recovery == animation length).
- Headless Chrome (CDP) driving the real page: select the character, run every move, assert state/frame/health/console.
- Regression: full existing pytest suite; assert default fighters' frame selection unchanged via the same browser run.
