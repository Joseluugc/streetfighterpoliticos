---

description: "Task list for Core Combat Engine & Dummy Character"
---

# Tasks: Core Combat Engine & Dummy Character

**Input**: Design documents from `/specs/001-core-combat-engine/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/module-interfaces.md, quickstart.md

**Tests**: INCLUDED. The constitution's Quality Gates require headless pytest coverage of FSM
transitions, hitbox/hurtbox resolution, fixed-timestep stepping and spritesheet validation, and the
plan lists the test files. Within each phase, write tests first and confirm they fail.

**Organization**: Tasks are grouped by user story (US1-US4, priority order from spec.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 Idle, US2 Move/Jump, US3 Melee/Guard, US4 Special projectile
- All paths are relative to the repository root. Units: pixels, pixels/update, updates (1/60 s).
- Tasks touching `src/entities/fighter.py`, `src/engine/game.py` or `src/engine/renderer.py` are
  NOT marked [P] across stories because they edit the same file.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, dependencies, test harness

- [X] T001 Create package directories with empty `__init__.py` files: `src/`, `src/config/`, `src/engine/`, `src/entities/`, `src/utils/`, plus `tests/unit/`, `tests/integration/` and `assets/characters/`
- [X] T002 Create `requirements.txt` pinning `pygame==2.6.1` and `pytest==8.3.4` (exact pins per constitution; Python 3.10+)
- [X] T003 [P] Create `pytest.ini` with `testpaths = tests` and `pythonpath = .`
- [X] T004 [P] Create `tests/conftest.py`: set `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` before importing pygame, call `pygame.init()` once per session, and add a fixture `sheet_path(tmp_path)` that writes a 3x3 grid PNG (128x192 cells, each cell filled with a distinct color) for tests
- [X] T005 [P] Real art supplied (`assets/characters/dummy.png`, 1024x572, 5+4 poses); replaced the placeholder generator with `scripts/measure_sheet.py`, which measures each frame rectangle and prints the `frames` JSON for `assets/characters/dummy.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, sprite slicing, collision primitives, input, FSM table, fighter skeleton, game loop shell

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Create `assets/characters/dummy.json` exactly as in `contracts/module-interfaces.md` ("Character config file")
- [X] T007 [P] Implement `src/config/settings.py`: constants `LOGICAL_WIDTH=960`, `LOGICAL_HEIGHT=540`, `FLOOR_Y=440`, `STAGE_LEFT=0`, `STAGE_RIGHT=960`, `UPDATES_PER_SECOND=60`, `MAX_CATCHUP_STEPS=5`; frozen dataclasses `Stage`, `KeyScheme` (A/D move, W jump, J punch, K kick, L guard, I special, F1 debug; training keys 1 punch, 2 kick, 3 guard, 4 special) and `CharacterConfig`/`AttackConfig`/`ProjectileConfig`; function `load_character_config(path) -> CharacterConfig` that raises `ConfigError` naming the file when a required key is missing
- [X] T008 [P] Write tests in `tests/unit/test_spritesheet.py`: loads 3x3 sheet into exactly 9 frames, `frame(i, +1)` and `frame(i, -1)` are mirrored, missing file raises `SpriteSheetError` containing the path, wrong image size raises `SpriteSheetError`, `cols*rows != 9` raises `SpriteSheetError`
- [X] T009 Implement `src/utils/spritesheet.py` per contract: `SpriteSheetError`, `SpriteSheet.load(path, cols, rows, cell_w, cell_h)` validating "image size == cols*cell_w x rows*cell_h" and "cols*rows == 9", slicing once with `subsurface(...).copy()` in row-major order, pre-flipping left-facing copies via `pygame.transform.flip`, and `frame(index, facing)` returning cached surfaces only (depends on T008)
- [X] T010 [P] Write tests in `tests/unit/test_physics.py`: hit registers when hitbox overlaps opposing hurtbox; no hit on own hurtbox (`owner_id` equal); one hit per hitbox via `already_hit`; no hit when rects do not overlap; `is_blocking` callback sets `HitEvent.blocked`
- [X] T011 Implement `src/engine/physics.py`: separate slotted dataclasses `Hurtbox(rect, owner_id)` (no attack data) and `Hitbox(rect, owner_id, damage, knockback, hitstun, blockstun, already_hit: set[int])`, frozen `HitEvent(attacker_id, defender_id, hitbox, blocked)`, pure `resolve_hits(hitboxes, hurtboxes, is_blocking)` that never tests a fighter's own boxes or sprite rects, and helper `place_box(x, y, facing, w, h, offset_x, offset_y) -> pygame.Rect` that mirrors `offset_x` by facing (depends on T010)
- [X] T012 [P] Implement `src/engine/input.py`: dataclass `Commands` (left, right, jump, punch, kick, guard, special; all bool, default False) with method `resolved()` applying "Both left and right true → treated as neither" and the priority "guard > special > kick > punch > jump > walk" (returns a Commands with only the winning action set), and `InputMapper.read(keys, scheme) -> Commands`
- [X] T013 [P] Write tests in `tests/unit/test_states_fsm.py`: all 8 required states plus `HIT_STUN` exist in the enum; every state in `STATE_TABLE` has a spec; allowed/forbidden transitions match the table in `data-model.md`; `Fighter.change_state` raises `InvalidTransition` for an undeclared transition (e.g. PUNCHING → WALKING) and accepts a declared one (depends on T015 for the Fighter cases)
- [X] T014 Implement `src/entities/states.py`: `FighterState` Enum (IDLE, WALKING, JUMPING, FALLING, PUNCHING, KICKING, DEFENDING, SPECIAL, HIT_STUN), frozen `StateSpec(frames, frame_hold, duration, interruptible, next)`, and `STATE_TABLE` with frame indices IDLE (0,1), WALKING (2,), JUMPING (3,), FALLING (4,), PUNCHING (5,), KICKING (6,), DEFENDING (7,), SPECIAL (8,), HIT_STUN (0,) and the transition table from `data-model.md` (states are an enum, never strings or boolean flags)
- [X] T015 Create `src/entities/fighter.py` skeleton: `InvalidTransition`, class `Fighter(fighter_id, x, config)` with fields `x, y=FLOOR_Y, vx, vy, facing, health=100 (clamped 0..100), state=IDLE, state_timer, frame_timer, jump_dir, hurtbox, active_hitbox=None`, read-only `position` and `frame_index` (derived from `STATE_TABLE[state].frames`), `change_state(new_state)` enforcing `STATE_TABLE[...].next` (raise `InvalidTransition`), and a stub `update(commands, opponent, stage) -> list`; NO pygame drawing and NO key-code reads (depends on T007, T011, T014)
- [X] T016 [P] Write tests in `tests/unit/test_timestep.py`: the accumulator runs exactly N updates for N/60 s of elapsed time, never more than `MAX_CATCHUP_STEPS` (5) per rendered frame, and `Game.update()` takes no time argument (depends on T018)
- [X] T017 Implement `src/engine/renderer.py` (basic): `Renderer(screen, sheets)` with `draw(game)` that fills the stage background, draws the floor line, blits each fighter's `sheets[...].frame(fighter.frame_index, fighter.facing)` at its position (feet-anchored at `y`), and draws a health bar per fighter (0-100) at the top; read-only access to game state (depends on T009, T015)
- [X] T018 Implement `src/engine/game.py` (shell): `Game(headless=False)` creates the 960x540 surface, loads `assets/characters/dummy.json` and the sheet once, creates two `Fighter`s (player at x=300, training dummy at x=660), a `Renderer`, and lists `projectiles`, `debug_overlay=False`; `update(commands_p1, commands_p2)` performs ONE 1/60 s step (no `dt`); `run()` uses the accumulator loop (add real elapsed time, while accumulator >= 1/60 run one `update` up to 5 per frame, discard the excess, render once, `Clock.tick(60)`); handle window close and F1 toggle (depends on T012, T015, T017)
- [X] T019 Create `src/main.py` entry point calling `Game().run()` so `python -m src.main` starts the game; show a clear error and exit non-zero on `SpriteSheetError`/`ConfigError` (FR-002) (depends on T018)

**Checkpoint**: Window opens, both Dummies are drawn on the floor with health bars; foundational tests pass.

---

## Phase 3: User Story 1 - Idle animation (Priority: P1) 🎯 MVP

**Goal**: Dummy alternates frames 1 and 2 every 30 updates while no input is given.

**Independent Test**: Launch the game and press nothing; frames alternate 1/2 every 0.5 s with no drift for 60 s.

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T020 [US1] Write `tests/integration/test_idle_animation.py`: new match shows frame index 0 (frame 1); after 30 updates index 1, after 60 index 0; over 3600 updates (60 s) only indices 0 and 1 appear and each switch is every 30 ±1 updates; after any other state ends with no input, Idle restarts at frame 0 (SC-002, SC-003)

### Implementation for User Story 1

- [X] T021 [US1] In `src/entities/fighter.py` implement Idle behavior: on `enter` IDLE reset `frame_timer=0`; each `update` in IDLE increment `frame_timer` and toggle `frame_index` between the two IDLE frames every `idle_frame_hold` (30) updates; `frame_index` always derived from state + timer (FR-003, FR-004)
- [X] T022 [US1] In `src/engine/game.py` call `fighter.update(...)` for both fighters each step in order (player then training dummy) with empty `Commands` for the dummy, and verify the renderer in `src/engine/renderer.py` uses `frame_index` and mirrors by `facing` (FR-005)

**Checkpoint**: US1 is fully functional — MVP demo: idle Dummy "breathing" at a steady rhythm.

---

## Phase 4: User Story 2 - Walk, jump and fall (Priority: P2)

**Goal**: Walk at constant speed within the stage; jump with a deterministic gravity arc; frames 3/4/5.

**Independent Test**: Hold A/D and tap W on an empty stage; Dummy stays inside the stage, arc is identical each time, frame matches phase.

### Tests for User Story 2 ⚠️

- [X] T023 [US2] Write `tests/unit/test_fighter_movement.py`: right held → x increases 4 px/update and frame index 2 (frame 3); release → IDLE next update; boundary clamp at 0 and 960; left+right together → stays IDLE; jump from floor → JUMPING (frame idx 3) with vy=-14 then FALLING (idx 4) once vy >= 0; no second jump while airborne; horizontal direction fixed at take-off; landing sets `y == FLOOR_Y` exactly, never below, then IDLE (or WALKING if a direction is held)
- [X] T024 [US2] Write `tests/integration/test_movement_jump.py`: ten consecutive identical jumps reach the same peak height and take the same number of updates (SC-004); two fighters on the ground cannot overlap/pass each other and auto-face each other; after a jump over the opponent, facing flips once the jumper lands (FR-011)

### Implementation for User Story 2

- [X] T025 [US2] In `src/entities/fighter.py` implement WALKING: from IDLE/WALKING with exactly one of left/right set, `vx = ±walk_speed (4)`, state WALKING (frame idx 2), back to IDLE when released; clamp x to `[STAGE_LEFT, STAGE_RIGHT]` using the hurtbox half-width (FR-007)
- [X] T026 [US2] In `src/entities/fighter.py` implement JUMPING/FALLING: jump command only when grounded (IDLE/WALKING) → `vy = jump_velocity (-14)`, `jump_dir` locked from held direction at take-off; each update `vy += gravity (0.7)`, `y += vy`; JUMPING while `vy < 0`, FALLING when `vy >= 0`; landing when `y >= FLOOR_Y`: set `y = FLOOR_Y`, `vy = 0`, go to IDLE/WALKING; airborne states ignore walk/attack/guard/special commands (FR-008, FR-009, FR-010)
- [X] T027 [US2] In `src/entities/fighter.py` implement auto-facing and ground separation: when both fighters are grounded set `facing` toward the opponent; prevent overlap of grounded hurtboxes by stopping the mover at the opponent's edge (FR-011)
- [X] T028 [US2] In `src/engine/game.py` wire the player's `Commands` from `InputMapper` (A/D/W) each step and keep the training dummy idle; in `src/engine/renderer.py` nothing new is required beyond frames 3/4/5 (verify only)

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Punch, kick and guard (Priority: P3)

**Goal**: Melee attacks with wind-up/active/recovery, hit-once damage, hit stun, blocking, health display, debug boxes.

**Independent Test**: Attack the training dummy for 5/8 damage per hit; make it attack (debug keys) while guarding to see 0 damage; F1 shows boxes.

### Tests for User Story 3 ⚠️

- [X] T029 [US3] Write `tests/unit/test_fighter_combat.py`: punch timing 4 startup / 3 active / 8 recovery then IDLE (frame idx 5); kick 7 / 4 / 12 (idx 6) with larger reach and damage 8; walk/jump/new attacks ignored until recovery ends; hitbox exists only during active frames; guard held → DEFENDING (idx 7), no movement, ends when released; guard rejects hits from behind (not blocked); hit interrupts the target's current action into HIT_STUN for 15 updates; block applies blockstun 8 and stays DEFENDING; health never below 0 or above 100
- [X] T030 [US3] Write `tests/integration/test_melee_guard.py`: in range punch → opponent loses exactly 5 once even when overlapping many updates; kick → 8; out-of-range or behind → 0 damage; guarding facing opponent → 0 damage and slight push-back; guarding but hit from behind → full damage; both fighters hit on the same update → both lose health (trade); 50 test attacks each deal damage exactly once or not at all (SC-005); command priority guard > special > kick > punch > jump > walk when several pressed together

### Implementation for User Story 3

- [X] T031 [US3] In `src/entities/fighter.py` implement PUNCHING and KICKING states: start only from grounded IDLE/WALKING; use `state_timer` over startup/active/recovery from `AttackConfig`; during active frames create `active_hitbox = Hitbox(place_box(...), owner_id, damage, knockback, hitstun, blockstun, set())`, otherwise `None`; return to IDLE after recovery (FR-012, FR-013, FR-014)
- [X] T032 [US3] In `src/entities/fighter.py` implement DEFENDING and `HIT_STUN`: guard command from grounded IDLE/WALKING → DEFENDING while held, `vx = 0`; add `is_blocking(hitbox)` (true only if DEFENDING and the attacker is on the side the fighter faces); implement `apply_hit(event)`: if blocked → no damage, push back by knockback/2, blockstun 8, remain DEFENDING; else subtract damage (clamp 0), push back, enter HIT_STUN for `hitstun` (15) updates, cancel any attack in progress and clear `active_hitbox` (FR-016, FR-017, FR-018, FR-019)
- [X] T033 [US3] In `src/engine/game.py` after fighters update: collect each fighter's `active_hitbox`, build hurtbox list, call `physics.resolve_hits(hitboxes, hurtboxes, is_blocking)` and apply each `HitEvent` via `defender.apply_hit(event)`; ensure both fighters receive hits from the same update (trade) (FR-015)
- [X] T034 [US3] In `src/engine/game.py` add training-dummy debug control: while the training keys (1 punch, 2 kick, 3 hold guard, 4 special) are held, build the dummy's `Commands`; the player's J/K/L map to punch/kick/guard through `InputMapper` and `Commands.resolved()` priority (FR-024, FR-025)
- [X] T035 [US3] In `src/engine/renderer.py` add the debug overlay (toggle `debug_overlay` with F1): draw hurtboxes in green, active hitboxes in red, projectile boxes in yellow, as outlines only (FR-026); keep health bars updating from `fighter.health`

**Checkpoint**: US1-US3 work independently; Dummy can trade, block, and be debugged visually.

---

## Phase 6: User Story 4 - "Ley de Vivienda" special (Priority: P4)

**Goal**: Frame 9 cast releases an independent forward-moving projectile with its own box and 90-update lifetime.

**Independent Test**: Press I on an empty stage — projectile crosses and disappears; at the training dummy, damage 10 once, or blocked when guarding.

### Tests for User Story 4 ⚠️

- [X] T036 [US4] Write `tests/unit/test_projectile.py`: moves `speed` px/update in the caster's facing direction; `lifetime` 90 decrements and sets `alive=False` at 0; leaves stage bounds → dead; `kill()` sets dead; own hitbox follows position and deals damage 10 once; never hits its owner
- [X] T037 [US4] Write `tests/integration/test_special_projectile.py`: Special from grounded IDLE/WALKING shows frame idx 8 for the whole 12 + 18 update cast and locks other actions; exactly one projectile spawns at the end of update 12 at the configured chest-height offset; projectile keeps moving if the caster moves, jumps or is hit; Special ignored (no cast, no new projectile) while own projectile is alive; hit on opponent → 10 damage once (or 0 if guarding and facing) and projectile vanishes immediately; miss → vanishes within 90 updates (SC-007); owner takes no damage when overlapping own projectile; two opposing projectiles pass through each other

### Implementation for User Story 4

- [X] T038 [US4] Implement `src/entities/projectile.py`: class `Projectile(owner_id, x, y, facing, config)` with `vx = facing * speed`, `lifetime = 90`, `alive=True`, `hitbox` (own `pygame.Rect` from config box, damage 10, owner_id) repositioned every update; `update(stage)` moves, decrements lifetime and sets `alive=False` on lifetime 0 or leaving `[STAGE_LEFT, STAGE_RIGHT]`; `kill()`; no pygame drawing (FR-022, FR-023)
- [X] T039 [US4] In `src/entities/fighter.py` implement SPECIAL state: start from grounded IDLE/WALKING only when the caller reports no own live projectile (pass `has_projectile` into `update`); frame idx 8 for the full cast (`startup` 12 + `recovery` 18); `update` returns `[Projectile(...)]` on the update where the wind-up ends (exactly once) spawned at `spawn_offset` mirrored by facing; return to IDLE after recovery (FR-020, FR-021)
- [X] T040 [US4] In `src/engine/game.py` maintain `projectiles`: compute `has_projectile` per owner, add spawned projectiles, update them each step, include their hitboxes in `resolve_hits` (skip owner's hurtbox), on a `HitEvent` call `projectile.kill()` (damaging or blocked), and remove dead projectiles at the end of each step
- [X] T041 [US4] In `src/engine/renderer.py` draw each live projectile as a placeholder shape/sprite at its position and include its hitbox in the debug overlay (yellow)

**Checkpoint**: All four user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T042 [P] Write `tests/integration/test_game_smoke.py`: headless `Game` runs 120 updates and renders 10 frames without errors, and a missing `dummy.png` raises `SpriteSheetError` naming the file (FR-002)
- [X] T043 Verify determinism (Principle IV): scripted `Commands` sequence run twice yields identical positions, health and states; ensure no module in `src/entities/` or `src/engine/physics.py` imports `time` or reads the clock
- [X] T044 Audit Principle I: confirm no `pygame.draw`/`display`/blit in `src/entities/` or `src/engine/physics.py`, no key-code reads outside `src/engine/input.py`, and no magic gameplay numbers outside `assets/characters/dummy.json` / `src/config/settings.py`
- [X] T045 [P] Add type hints and PEP 8 formatting to all public classes/methods in `src/`
- [X] T046 Performance: 3600 headless update+render steps run at ~1600 steps/s (>= 60 required); window loop ran 3 s without errors (a full 5-minute windowed run is still worth doing by hand)
- [X] T047 Run the full `quickstart.md` validation: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest -q` then every manual row
- [ ] T048 Recommend amending Constitution Principle V wording ("one 9-frame sheet per character; each state maps to one animation of 1+ frames") via `/speckit-constitution` and note the outcome in `specs/001-core-combat-engine/plan.md` Complexity Tracking

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories
- **US1 (P1)**: after Foundational — no story dependencies (MVP)
- **US2 (P2)**: after Foundational — builds on the Fighter from US1 but testable independently
- **US3 (P3)**: after Foundational; uses movement/facing from US2 for spacing in tests
- **US4 (P4)**: after US3 (reuses hit resolution, blocking, `apply_hit`)
- **Polish (Phase 7)**: after the desired stories are complete

### Within Foundational

T006/T007 → T015; T008 → T009; T010 → T011 → T015; T014 → T015; T015 + T009 → T017 → T018 → T019; T016 depends on T018; T013 Fighter cases depend on T015.

### Within Each User Story

Tests first (fail) → fighter logic → game wiring → renderer. Tasks editing `fighter.py`, `game.py` or `renderer.py` run sequentially.

## Parallel Examples

```text
# Setup:
T003 pytest.ini  |  T004 tests/conftest.py  |  T005 scripts/make_placeholder_sheet.py

# Foundational (different files):
T006 dummy.json  |  T007 config/settings.py  |  T008 test_spritesheet  |  T010 test_physics  |  T012 input.py

# After T009 and T011:
T009 spritesheet.py  |  T011 physics.py  |  T014 states.py

# US3 tests (different files):
T029 test_fighter_combat.py  |  T030 test_melee_guard.py

# US4 tests:
T036 test_projectile.py  |  T037 test_special_projectile.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1
2. STOP and validate: idle Dummy alternates frames 1/2 every 0.5 s
3. Demo, then continue

### Incremental Delivery

1. Setup + Foundational → window with two Dummies
2. US1 (idle) → US2 (walk/jump) → US3 (melee/guard + debug overlay) → US4 (projectile special)
3. Each story passes its own tests before the next begins; Polish last

## Notes

- Tune gameplay values only in `assets/characters/dummy.json`, never in code (constitution).
- If the user supplies real art for `dummy.png`, read its size first and update `grid` in `dummy.json`.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
