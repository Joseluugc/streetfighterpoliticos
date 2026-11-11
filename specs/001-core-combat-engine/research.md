# Phase 0 Research: Core Combat Engine & Dummy Character

All Technical Context unknowns are resolved below. No `NEEDS CLARIFICATION` items remain.

## R1. Runtime & library versions

- **Decision**: Python 3.10+ (target 3.12), `pygame` 2.6.x, `pytest` 8.x for tests.
- **Rationale**: Constitution mandates Python 3 + Pygame (>= 3.10 for `match` and modern typing
  syntax). pygame 2.x supports `pygame.Rect`, `Surface.subsurface`, and the `SDL_VIDEODRIVER=dummy`
  headless mode needed by the constitution's testing gate.
- **Alternatives considered**: `pygame-ce` (community fork) — rejected to stay on the library
  named in the constitution; arcade/pyglet — violate the Pygame-only rule.

## R2. Fixed timestep loop

- **Decision**: Accumulator loop. Each rendered frame adds elapsed real time to an accumulator;
  while `accumulator >= 1/60 s` run one `update()` (max 5 steps per frame, extra time is
  discarded), then render once. `pygame.time.Clock.tick(60)` caps rendering/CPU use. Simulation
  receives no time argument: one call = one update (frame-counted timings per Principle IV).
- **Rationale**: Gives deterministic simulation independent of render rate; the step cap avoids
  the spiral of death. Because `update()` takes no `dt`, tests can step it directly.
- **Alternatives considered**: Variable `dt` physics — non-deterministic, violates Principle IV.
  Simple `clock.tick(60)` with one update per frame — slows the game when rendering lags.

## R3. Simulation/rendering separation

- **Decision**: `Game` (in `src/engine/game.py`) owns the loop and a `Renderer`
  (`src/engine/renderer.py`). Fighters/projectiles never import `pygame.draw` or blit; they expose
  read-only state (position, facing, `current_frame_index`, boxes) that the renderer reads.
- **Rationale**: The requested `game.py` "main loop and rendering logic" is honored (game.py runs
  the render step) while Principle I's rule that logic classes must not draw is kept; drawing code
  lives in one class called from game.py.
- **Alternatives considered**: Drawing inside `Fighter.draw()` — simplest but violates Principle I.

## R4. Spritesheet layout & slicing

- **Decision**: One PNG per character, a **3 x 3 grid** of equal cells read left-to-right,
  top-to-bottom, giving frames 1-9. Grid size, cell size, and the state→frame mapping are declared
  in `assets/characters/<name>.json`. `SpriteSheet.load()` validates image size equals
  `cols*cell_w` x `rows*cell_h` and that `cols*rows == 9`, slices with `subsurface().copy()` once
  at load, and caches the list of 9 surfaces. Mirrored (left-facing) surfaces are pre-computed at
  load via `pygame.transform.flip`.
- **Rationale**: Matches the user's "9-frame grid PNG"; data-driven per Principle V; pre-flipping
  avoids per-frame transforms in the loop.
- **Alternatives considered**: Horizontal strip of 9 frames — fine but less compact; per-frame PNG
  files — contradicts the single-sheet requirement.

## R5. Constitution Principle V wording

- **Decision**: Treat Principle V as "each character sheet has exactly 9 frames; each FSM state maps
  to one animation (a list of 1+ frame indices of that sheet)". Idle's animation is `[0, 1]`
  (frames 1 & 2); every other state uses one frame.
- **Rationale**: The spec requires frames 3-9 to be single poses, so "each animation = 9 frames" is
  impossible. Recorded in the plan's Complexity Tracking; a PATCH/MINOR amendment of Principle V
  via `/speckit-constitution` is recommended (not done by this command).
- **Alternatives considered**: Animate each state with 9 frames — contradicts spec and art budget.

## R6. Hitbox / hurtbox resolution

- **Decision**: `Hitbox` and `Hurtbox` are separate frozen/slotted dataclasses holding a
  `pygame.Rect` (world-space, recomputed each update from fighter position, facing and
  per-state offsets). `physics.resolve_hits(attackers, defenders)` is a pure function that
  returns `HitEvent`s (attacker, defender, hitbox, blocked). A hitbox keeps a set of already-hit
  target ids so one attack hits once. Block is resolved when the event is applied: defender is
  `DEFENDING` and faces the attacker (attacker's x on the facing side) → blocked.
- **Rationale**: Pure functions are trivially unit-testable headless; matches Principle III.
- **Alternatives considered**: Using `pygame.sprite.collide_rect` on sprite rects — violates the
  "never sprite rectangles" rule.

## R7. FSM implementation

- **Decision**: `FighterState` is an `Enum` (IDLE, WALKING, JUMPING, FALLING, PUNCHING, KICKING,
  DEFENDING, SPECIAL, HIT_STUN). A `STATE_TABLE: dict[FighterState, StateSpec]` declares per state:
  animation frame indices, duration (frames, or `None` for held states), whether interruptible,
  and the allowed next states. `Fighter.change_state(new)` rejects undeclared transitions by
  raising `InvalidTransition` in debug/tests and ignoring in release play (command is dropped).
  `enter/update/exit` are implemented as methods dispatched by state (`_enter_<state>` etc.) to
  avoid 9 near-empty classes while still meeting Principle II.
- **Rationale**: Table-driven transitions are testable and declarative; simpler than the State
  pattern with one class per state for a game this size.
- **Alternatives considered**: One class per state — heavier boilerplate; boolean flags — banned by
  constitution.

## R8. Input & training dummy control

- **Decision**: `InputMapper` converts pygame key state into a `Commands` dataclass of booleans
  (left, right, jump, punch, kick, guard, special) every update. The training dummy receives either
  empty commands or commands from debug keys (1 punch, 2 kick, 3 hold guard, 4 special; F1 toggles
  overlay). Fighters consume only `Commands`.
- **Rationale**: Principle I — fighters never read key codes; tests can feed `Commands` directly.
- **Alternatives considered**: Event-based input — misses held-key semantics needed for walk/guard.

## R9. Gameplay numbers & physics units

- **Decision**: Logical resolution 960x540 scaled to window; floor at y = 440; units are pixels and
  pixels/update. Walk 4 px/update; jump initial velocity -14, gravity +0.7 per update (peak
  ~140 px, ~40 updates in air); hitbox/hurtbox values and frame data from the spec's table, stored
  in `assets/characters/dummy.json` and `src/config/settings.py`.
- **Rationale**: Constitution requires config-driven tunables; values give a readable arc at 60 Hz.
- **Alternatives considered**: Hardcoded constants in classes — banned.

## R10. Testing strategy

- **Decision**: pytest, headless via `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` set in
  `tests/conftest.py`. Unit tests for FSM, physics, spritesheet, projectile, timestep accumulator;
  integration tests drive `Game.update()` with scripted `Commands` for each user story's scenarios.
  A smoke test starts `Game`, runs 120 updates and renders 10 frames.
- **Rationale**: Satisfies the constitution's headless-testing gate.
- **Alternatives considered**: Manual-only testing — rejected by constitution.

## Addendum: real sheet layout (supersedes R4's 3x3 assumption)

The supplied art (`assets/characters/dummy.png`, 1024x572) is **not** a uniform grid: 5 poses on the
top row, 4 on the bottom row, on a flat gray background, with the scroll projectile drawn beside
frame 9. Decision: `SpriteSheet.load(path, frames, background_tolerance, scale, extras)` takes an
explicit list of 9 `FrameRect`s (x, y, w, h, anchor_x, foot_y) from `dummy.json`, makes the gray
background transparent once at load, scales by `sprite_scale` (0.72), and also cuts the projectile
sprite as an extra. The "exactly 9 frames" rule is still validated. `scripts/measure_sheet.py`
generates the rectangles. Stage is 1024x572 to match `assets/background.png`; floor at y=520.
