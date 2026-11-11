# Data Model: Core Combat Engine & Dummy Character

Units: pixels, pixels per update, and updates (1 update = 1/60 s). Defaults come from the spec's
"Default Gameplay Values" table and live in `assets/characters/dummy.json` / `src/config/settings.py`.

## Entities

### Commands (input snapshot, `src/engine/input.py`)

| Field | Type | Notes |
|-------|------|-------|
| left, right | bool | Both true → treated as neither (spec edge case) |
| jump, punch, kick, guard, special | bool | Priority when several: guard > special > kick > punch > jump > walk |

### FighterState (enum, `src/entities/states.py`)

`IDLE, WALKING, JUMPING, FALLING, PUNCHING, KICKING, DEFENDING, SPECIAL, HIT_STUN`

### StateSpec (frozen dataclass, one per state in `STATE_TABLE`)

| Field | Type | Notes |
|-------|------|-------|
| frames | tuple[int, ...] | Zero-based sheet indices: IDLE (0,1); WALKING (2,); JUMPING (3,); FALLING (4,); PUNCHING (5,); KICKING (6,); DEFENDING (7,); SPECIAL (8,); HIT_STUN (0,) |
| frame_hold | int | Updates each frame is shown (IDLE = 30, others irrelevant) |
| duration | int or None | Total updates; None = held/condition-driven (IDLE, WALKING, DEFENDING, JUMPING, FALLING) |
| interruptible | bool | Whether commands may leave the state early |
| next | frozenset[FighterState] | Declared legal transitions |

### Transition table

| From | To (allowed) |
|------|--------------|
| IDLE | WALKING, JUMPING, PUNCHING, KICKING, DEFENDING, SPECIAL, HIT_STUN |
| WALKING | IDLE, JUMPING, PUNCHING, KICKING, DEFENDING, SPECIAL, HIT_STUN |
| JUMPING | FALLING, HIT_STUN |
| FALLING | IDLE, WALKING, HIT_STUN |
| PUNCHING | IDLE, HIT_STUN (when duration ends or hit) |
| KICKING | IDLE, HIT_STUN |
| DEFENDING | IDLE, WALKING, HIT_STUN (hit while blocking stays DEFENDING; see block rule) |
| SPECIAL | IDLE, HIT_STUN |
| HIT_STUN | IDLE |

Any transition not listed is rejected. Airborne states accept no attack/guard/special commands.

### Fighter (`src/entities/fighter.py`)

| Field | Type | Rules |
|-------|------|-------|
| id | int | Unique; used by hitboxes to prevent self-hit and double-hit |
| x, y | float | `y` is the feet position; floor y = 440; never below floor |
| vx, vy | float | Walk 4 px/update; jump vy -14, gravity +0.7 |
| facing | int (+1 / -1) | Auto-faces opponent when both grounded (FR-011) |
| health | int | 0..100, starts 100, clamped (FR-019) |
| state, state_timer, frame_timer | enum, int, int | Timers count updates |
| jump_dir | int (-1, 0, +1) | Locked at take-off (FR-009) |
| has_projectile | bool | Derived from the world's live projectiles owned by this fighter |
| hurtbox | Hurtbox | Re-positioned every update |
| active_hitbox | Hitbox or None | Exists only during an attack's active window |

Validation: health clamp; position clamp to stage bounds; no overlap with opponent on the ground.

### Hurtbox / Hitbox (`src/engine/physics.py`, separate types)

| Entity | Fields |
|--------|--------|
| Hurtbox | `rect: pygame.Rect` (world space), `owner_id: int` — no attack data |
| Hitbox | `rect`, `owner_id`, `damage`, `knockback`, `hitstun`, `blockstun`, `already_hit: set[int]` |
| HitEvent | `attacker_id`, `defender_id`, `hitbox`, `blocked: bool` |

Attack frame data (updates): Punch 4 wind-up / 3 active / 8 recovery, damage 5; Kick 7 / 4 / 12,
damage 8; Special 12 wind-up (projectile spawns on last wind-up update) / 18 recovery, projectile
damage 10. Hit stun 15, block stun 8.

### Projectile ("Ley de Vivienda", `src/entities/projectile.py`)

| Field | Type | Rules |
|-------|------|-------|
| owner_id | int | Never damages owner (FR-023) |
| x, y | float | Spawns in front of caster at chest height |
| vx | float | Constant, sign = caster facing |
| lifetime | int | 90 updates, decremented each update |
| hitbox | Hitbox | Own rect; damage 10; one hit only |
| alive | bool | False on hit, off-stage, or lifetime 0 |

### Stage (`src/engine/game.py` config)

`width=960`, `floor_y=440`, `left=0`, `right=960`; contains fighters and projectiles.

### SpriteSheet (`src/utils/spritesheet.py`)

| Field | Notes |
|-------|-------|
| frames_right / frames_left | `list[pygame.Surface]`, exactly 9 each, indices 0-8 |
| grid | cols=3, rows=3, cell size from config |

Validation: file exists; image size == grid x cell; `cols*rows == 9`; error names the file.

## Relationships

- `Game` 1 — 2 `Fighter`; `Game` 1 — 0..2 `Projectile` (max one per owner).
- `Fighter` 1 — 1 `Hurtbox`; `Fighter` 1 — 0..1 active `Hitbox`; `Projectile` 1 — 1 `Hitbox`.
- `Fighter` 1 — 1 `SpriteSheet` (shared by reference between same-character fighters).
- `physics.resolve_hits` consumes hitboxes + hurtboxes and produces `HitEvent`s; `Game` applies them.
