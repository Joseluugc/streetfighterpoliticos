# Module Interface Contracts

Internal contracts between modules (the game has no network/CLI surface). Signatures are the
required public API; bodies are left to implementation. All public classes use type hints (PEP 8).

## `src/utils/spritesheet.py`

```python
class SpriteSheetError(Exception): ...        # message MUST name the file

class SpriteSheet:
    @classmethod
    def load(cls, path: str, cols: int, rows: int, cell_w: int, cell_h: int) -> "SpriteSheet": ...
    def frame(self, index: int, facing: int) -> pygame.Surface: ...   # index 0..8, facing +1/-1
    frame_count: int                                                  # always 9
```

- Raises `SpriteSheetError` if the file is missing, `cols*rows != 9`, or image size mismatches.
- Slices and mirrors once in `load`; `frame()` only returns cached surfaces.

## `src/engine/physics.py`

```python
@dataclass(slots=True)
class Hurtbox: rect: pygame.Rect; owner_id: int
@dataclass(slots=True)
class Hitbox:  rect: pygame.Rect; owner_id: int; damage: int; knockback: int
               hitstun: int; blockstun: int; already_hit: set[int]
@dataclass(frozen=True, slots=True)
class HitEvent: attacker_id: int; defender_id: int; hitbox: Hitbox; blocked: bool

def resolve_hits(hitboxes: Sequence[Hitbox], hurtboxes: Sequence[Hurtbox],
                 is_blocking: Callable[[int, Hitbox], bool]) -> list[HitEvent]: ...
```

- Pure: no pygame display, no time, no mutation except adding the defender id to
  `hitbox.already_hit`.
- Never reports a hit where `hitbox.owner_id == hurtbox.owner_id` or where the defender id is already
  in `already_hit`.

## `src/entities/fighter.py` (+ `src/entities/states.py`)

```python
class InvalidTransition(Exception): ...

class Fighter:
    def __init__(self, fighter_id: int, x: float, config: CharacterConfig) -> None: ...
    def update(self, commands: Commands, opponent: "Fighter", stage: Stage) -> list[Projectile]: ...
    def change_state(self, new_state: FighterState) -> None: ...      # enforces STATE_TABLE
    def apply_hit(self, event: HitEvent) -> None: ...                 # damage/knockback/stun/block
    # read-only for the renderer:
    state: FighterState; facing: int; health: int
    position: tuple[float, float]; frame_index: int
    hurtbox: Hurtbox; active_hitbox: Hitbox | None
```

- `update` advances exactly one simulation step and returns newly spawned projectiles (0 or 1).
- Contains no drawing calls and reads no key codes.

## `src/entities/projectile.py`

```python
class Projectile:
    def __init__(self, owner_id: int, x: float, y: float, facing: int, config: ProjectileConfig) -> None: ...
    def update(self, stage: Stage) -> None: ...        # moves vx, decrements lifetime, sets alive
    def kill(self) -> None: ...
    alive: bool; hitbox: Hitbox; owner_id: int; lifetime: int
```

## `src/engine/game.py`

```python
class Game:
    def __init__(self, headless: bool = False) -> None: ...
    def update(self, commands_p1: Commands, commands_p2: Commands) -> None: ...  # ONE 1/60 s step
    def run(self) -> None: ...                         # accumulator loop, render once per frame
    fighters: list[Fighter]; projectiles: list[Projectile]; debug_overlay: bool
```

- `update` order each step: fighters update → collect spawned projectiles → projectiles update →
  gather active hitboxes → `resolve_hits` → apply events → remove dead projectiles.
- `run` caps catch-up at 5 updates per rendered frame.

## `src/engine/renderer.py` and `src/engine/input.py`

```python
class Renderer:
    def __init__(self, screen: pygame.Surface, sheets: dict[int, SpriteSheet]) -> None: ...
    def draw(self, game: Game) -> None: ...            # fighters, projectiles, health bars, overlay
class InputMapper:
    def read(self, keys: pygame.key.ScancodeWrapper, scheme: KeyScheme) -> Commands: ...
```

## Character config file: `assets/characters/dummy.json`

```json
{
  "name": "dummy",
  "sheet": "assets/characters/dummy.png",
  "grid": {"cols": 3, "rows": 3, "cell_w": 128, "cell_h": 192},
  "animations": {
    "IDLE": [0, 1], "WALKING": [2], "JUMPING": [3], "FALLING": [4],
    "PUNCHING": [5], "KICKING": [6], "DEFENDING": [7], "SPECIAL": [8]
  },
  "idle_frame_hold": 30,
  "walk_speed": 4, "jump_velocity": -14, "gravity": 0.7,
  "hurtbox": {"w": 70, "h": 170, "offset_x": 0},
  "attacks": {
    "PUNCH": {"startup": 4, "active": 3, "recovery": 8, "damage": 5, "reach": 40,
              "box": {"w": 45, "h": 30, "offset_x": 35, "offset_y": -120}},
    "KICK": {"startup": 7, "active": 4, "recovery": 12, "damage": 8, "reach": 60,
             "box": {"w": 65, "h": 35, "offset_x": 35, "offset_y": -70}}
  },
  "special": {"startup": 12, "recovery": 18, "projectile": {"speed": 7, "lifetime": 90,
              "damage": 10, "box": {"w": 40, "h": 30}, "spawn_offset": {"x": 50, "y": -110}}},
  "hitstun": 15, "blockstun": 8, "max_health": 100
}
```

Loading fails with a clear error naming the file when a required key is missing.
