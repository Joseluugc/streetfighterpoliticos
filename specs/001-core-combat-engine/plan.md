# Implementation Plan: Core Combat Engine & Dummy Character

**Branch**: `001-core-combat-engine` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-core-combat-engine/spec.md`

## Summary

Build the reusable combat engine and one generic Dummy fighter: idle animation, walking, jumping and
falling under gravity, punch, kick, guard, and the "Ley de Vivienda" projectile special. The
approach is a strictly layered Python/Pygame codebase under `src/`: a fixed-timestep `Game` loop
(60 updates/s), a table-driven FSM in `Fighter`, separate `Hitbox`/`Hurtbox` types resolved by pure
functions in `physics.py`, an independent `Projectile` entity, and a `SpriteSheet` utility that
slices a 3x3 grid PNG into 9 cached surfaces. All tunables live in JSON/config, and all
non-rendering logic is testable headless with pytest.

## Technical Context

**Language/Version**: Python 3.10+ (target 3.12)

**Primary Dependencies**: `pygame` 2.6.x (only runtime dependency)

**Storage**: Files only — character sheet PNG and character config JSON under `assets/characters/`

**Testing**: `pytest` 8.x, headless via `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy`

**Target Platform**: Desktop (Linux primary; Windows/macOS expected to work, not verified)

**Project Type**: Desktop game (single project)

**Performance Goals**: Stable 60 updates/s and 60 rendered FPS with 2 fighters + 2 projectiles

**Constraints**: Fixed 1/60 s simulation step, max 5 catch-up steps per rendered frame; all timings
in updates; deterministic simulation for identical inputs; no image loading/slicing in the loop

**Scale/Scope**: 2 fighters, 1 stage, 9 states, 1 projectile type, ~8 source modules, 960x540 logical
resolution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Strict OOP & separation of concerns | PASS | Layers: `Game` (loop), `InputMapper`, `Fighter`/`Projectile` (logic), `physics` (collision), `Renderer` (drawing), `SpriteSheet`/config loader (assets). Fighters get `Commands`, never key codes; no drawing in logic classes |
| II. FSM for character behavior | PASS | `FighterState` enum with the 8 required states (+ `HIT_STUN`), `STATE_TABLE` with declared transitions, animation derived from state |
| III. Separate hitbox/hurtbox | PASS | Distinct `Hitbox` (attack data, active frames, hit-once set) and `Hurtbox` types; resolution only hitbox-vs-opposing-hurtbox; debug overlay in `Renderer` |
| IV. 60 FPS fixed timestep | PASS | Accumulator loop, capped steps, `update()` takes no `dt`, all durations in updates |
| V. Spritesheet slice management | PASS with justified interpretation | One 9-frame grid sheet per character, data-driven, sliced once at load, fails loudly. See Complexity Tracking |
| Technical constraints | PASS | Python 3.10+, Pygame only, pinned deps, config-driven values, type hints |
| Workflow gates | PASS | pytest headless tests planned for FSM, physics, timestep, spritesheet; debug overlay included |

**Post-design re-check (after Phase 1)**: all gates still PASS. One deviation (Principle V wording)
is tracked below; the user-requested `game.py` "rendering logic" is satisfied by `game.py`
invoking a separate `Renderer`, preserving Principle I.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-combat-engine/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── module-interfaces.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
requirements.txt                 # pinned: pygame, pytest
assets/
└── characters/
    ├── dummy.png                # 3x3 grid, 9 frames (placeholder until real art)
    └── dummy.json               # grid, animations, physics, attacks, special, boxes

src/
├── __init__.py
├── main.py                      # entry point: python -m src.main → Game().run()
├── config/
│   ├── __init__.py
│   └── settings.py              # window/stage constants, KeyScheme, CharacterConfig loader (JSON → dataclasses)
├── engine/
│   ├── __init__.py
│   ├── game.py                  # Game: fixed-timestep loop (60 Hz), world update order, owns Renderer
│   ├── renderer.py              # Renderer: draws stage, fighters, projectiles, health bars, debug overlay
│   ├── input.py                 # Commands dataclass + InputMapper (keys → Commands, priority rules)
│   └── physics.py               # Hitbox, Hurtbox, HitEvent, resolve_hits(), box placement helpers
├── entities/
│   ├── __init__.py
│   ├── states.py                # FighterState enum, StateSpec, STATE_TABLE (transitions, frames, durations)
│   ├── fighter.py               # Fighter: FSM, movement/jump physics, attacks, guard, applies hits
│   └── projectile.py            # Projectile: "Ley de Vivienda" entity (own hitbox, speed, lifetime)
└── utils/
    ├── __init__.py
    └── spritesheet.py           # SpriteSheet: validate, crop 9-frame grid, cache + pre-mirror surfaces

tests/
├── conftest.py                  # sets SDL dummy drivers, shared fixtures (generated 3x3 test sheet)
├── unit/
│   ├── test_spritesheet.py
│   ├── test_states_fsm.py
│   ├── test_physics.py
│   ├── test_fighter_movement.py
│   ├── test_fighter_combat.py
│   ├── test_projectile.py
│   └── test_timestep.py
└── integration/
    ├── test_idle_animation.py   # User Story 1
    ├── test_movement_jump.py    # User Story 2
    ├── test_melee_guard.py      # User Story 3
    ├── test_special_projectile.py  # User Story 4
    └── test_game_smoke.py       # 120 updates + 10 renders, headless
```

**Structure Decision**: Single desktop-game project under `src/` with four packages by concern:
`engine` (loop, rendering, input, collision), `entities` (fighter FSM and projectile), `utils`
(spritesheet), and `config` (data loading). This matches the requested files
(`engine/game.py`, `engine/physics.py`, `entities/fighter.py`, `entities/projectile.py`,
`utils/spritesheet.py`) and adds only what the constitution requires: `renderer.py` (logic must not
draw), `input.py` (fighters take abstract commands), `states.py` (declarative FSM table), and
`config/` (no magic numbers).

### Module responsibilities

| File | Responsibility | Depends on |
|------|----------------|------------|
| `engine/game.py` | Accumulator loop, step order, apply `HitEvent`s, spawn/remove projectiles, toggle debug | fighter, projectile, physics, renderer, input |
| `engine/physics.py` | `Hitbox`/`Hurtbox` types, `resolve_hits`, rect placement from position + facing | pygame.Rect only |
| `entities/fighter.py` | FSM transitions, walk/jump/gravity, attack phases, guard, `apply_hit`, projectile spawn request | states, physics, config |
| `entities/projectile.py` | Move, countdown lifetime, own hitbox, stage-exit death | physics, config |
| `utils/spritesheet.py` | Validate and crop 3x3 PNG into 9 `Surface`s (plus mirrored), raise `SpriteSheetError` | pygame |
| `engine/renderer.py` | Blit frames by `fighter.frame_index`/`facing`, HUD, debug boxes | spritesheet, game state (read-only) |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle V read as "one 9-frame sheet per character; each state maps to one animation of 1+ frames" instead of "each animation has exactly 9 frames" | Spec fixes frames 1-9 to different poses (idle uses 1-2, every other state one pose) | Giving every animation 9 frames contradicts the spec and the supplied art layout. Recommend amending Principle V wording via `/speckit-constitution` |
| Extra files beyond the five requested (`renderer.py`, `input.py`, `states.py`, `config/settings.py`) | Constitution Principles I/II and the config rule require them | Putting drawing in `game.py`/`fighter.py`, key reads in `fighter.py`, or magic numbers in code violates the constitution |
