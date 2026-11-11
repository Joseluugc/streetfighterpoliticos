"""Fighter: table-driven FSM, movement/jump physics, melee, guard and special move.

Contains no drawing and no key-code reads. One `update()` call == one 1/60 s simulation step.
"""
from __future__ import annotations

from src.config.settings import AttackConfig, CharacterConfig, Stage
from src.engine.input import Commands
from src.engine.physics import HitEvent, Hitbox, Hurtbox, place_box
from src.entities.projectile import Projectile
from src.entities.states import STATE_TABLE, FighterState

S = FighterState
_AIRBORNE = (S.JUMPING, S.FALLING)
_FACING_STATES = (S.IDLE, S.WALKING, S.DEFENDING)
_PUSH_STEP = 4


class InvalidTransition(Exception):
    """Raised when a state change is not declared in STATE_TABLE."""


class Fighter:
    def __init__(self, fighter_id: int, x: float, config: CharacterConfig, stage: Stage | None = None,
                 facing: int = 1) -> None:
        self.id = fighter_id
        self.config = config
        self.stage = stage or Stage()
        self.x = float(x)
        self.y = float(self.stage.floor_y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = facing
        self.health = config.max_health
        self.state = S.IDLE
        self.state_timer = 0
        self.frame_timer = 0
        self.jump_dir = 0
        self.stun_duration = 0
        self.block_lock = 0
        self.push_remaining = 0
        self.push_dir = 0
        self.active_hitbox: Hitbox | None = None
        self.hurtbox = Hurtbox(place_box(self.x, self.y, self.facing, *self._hurt_args()), fighter_id)

    # ---- read-only views for the renderer -------------------------------------------------
    @property
    def position(self) -> tuple[float, float]:
        return self.x, self.y

    @property
    def frame_index(self) -> int:
        frames = STATE_TABLE[self.state].frames
        if self.state is S.IDLE:
            return frames[(self.frame_timer // self.config.idle_frame_hold) % len(frames)]
        return frames[0]

    @property
    def grounded(self) -> bool:
        return self.y >= self.stage.floor_y and self.state not in _AIRBORNE

    # ---- FSM ------------------------------------------------------------------------------
    def change_state(self, new_state: FighterState) -> None:
        if new_state is self.state:
            return
        if new_state not in STATE_TABLE[self.state].next:
            raise InvalidTransition(f"{self.state.name} -> {new_state.name} is not allowed")
        self.state = new_state
        self.state_timer = 0
        if new_state is S.IDLE:
            self.frame_timer = 0
        if new_state not in (S.PUNCHING, S.KICKING):
            self.active_hitbox = None

    # ---- simulation step ------------------------------------------------------------------
    def update(self, commands: Commands, opponent: "Fighter", stage: Stage | None = None,
               has_projectile: bool = False) -> list[Projectile]:
        stage = stage or self.stage
        cmd = commands.resolved()
        spawned: list[Projectile] = []
        prev_x = self.x
        self.state_timer += 1
        self.frame_timer += 1

        handler = {
            S.IDLE: self._free, S.WALKING: self._free, S.DEFENDING: self._defending,
            S.JUMPING: self._airborne, S.FALLING: self._airborne,
            S.PUNCHING: self._attack, S.KICKING: self._attack,
            S.SPECIAL: self._special, S.HIT_STUN: self._hit_stun,
        }[self.state]
        spawned.extend(handler(cmd, stage, has_projectile) or [])

        self._apply_push()
        self._separate(opponent, prev_x)
        half = self.config.hurtbox.w / 2
        self.x = min(max(self.x, stage.left + half), stage.right - half)
        if self.state in _FACING_STATES and self.grounded and opponent.grounded and opponent.x != self.x:
            self.facing = 1 if opponent.x > self.x else -1
        self._refresh_boxes()
        return spawned

    # ---- state handlers -------------------------------------------------------------------
    def _direction(self, cmd: Commands) -> int:
        return int(cmd.right) - int(cmd.left)

    def _free(self, cmd: Commands, stage: Stage, has_projectile: bool) -> None:
        if cmd.guard:
            self.vx = 0
            self.change_state(S.DEFENDING)
        elif cmd.special:
            if not has_projectile:
                self.vx = 0
                self.change_state(S.SPECIAL)
        elif cmd.kick:
            self.vx = 0
            self.change_state(S.KICKING)
        elif cmd.punch:
            self.vx = 0
            self.change_state(S.PUNCHING)
        elif cmd.jump:
            self.jump_dir = self._direction(cmd)
            self.vy = self.config.jump_velocity
            self.vx = 0
            self.change_state(S.JUMPING)
        else:
            direction = self._direction(cmd)
            self.vx = direction * self.config.walk_speed
            self.x += self.vx
            self.change_state(S.WALKING if direction else S.IDLE)

    def _defending(self, cmd: Commands, stage: Stage, has_projectile: bool) -> None:
        self.vx = 0
        if self.block_lock > 0:
            self.block_lock -= 1
        elif not cmd.guard:
            self.change_state(S.IDLE)

    def _integrate_air(self, stage: Stage) -> bool:
        """Apply gravity; return True when the fighter landed this update."""
        self.vy += self.config.gravity
        self.y += self.vy
        self.x += self.jump_dir * self.config.walk_speed
        if self.y >= stage.floor_y:
            self.y = float(stage.floor_y)
            self.vy = 0.0
            self.jump_dir = 0
            return True
        return False

    def _airborne(self, cmd: Commands, stage: Stage, has_projectile: bool) -> None:
        landed = self._integrate_air(stage)
        if landed:
            if self.state is S.JUMPING:
                self.change_state(S.FALLING)
            direction = self._direction(cmd)
            self.change_state(S.WALKING if direction else S.IDLE)
        elif self.state is S.JUMPING and self.vy >= 0:
            self.change_state(S.FALLING)

    def _attack_config(self) -> AttackConfig:
        return self.config.punch if self.state is S.PUNCHING else self.config.kick

    def _attack(self, cmd: Commands, stage: Stage, has_projectile: bool) -> None:
        atk = self._attack_config()
        t = self.state_timer
        if atk.startup < t <= atk.startup + atk.active:
            if self.active_hitbox is None:  # created once per attack so it can only hit once
                box = atk.box
                rect = place_box(self.x, self.y, self.facing, box.w, box.h, box.offset_x, box.offset_y)
                self.active_hitbox = Hitbox(rect, self.id, atk.damage, atk.knockback,
                                            self.config.hitstun, self.config.blockstun)
        else:
            self.active_hitbox = None
        if t >= atk.total:
            self.change_state(S.IDLE)

    def _special(self, cmd: Commands, stage: Stage, has_projectile: bool) -> list[Projectile]:
        sp = self.config.special
        spawned: list[Projectile] = []
        if self.state_timer == sp.startup:
            pc = sp.projectile
            spawned.append(Projectile(self.id, self.x + self.facing * pc.spawn_x, self.y + pc.spawn_y,
                                      self.facing, pc))
        if self.state_timer >= sp.total:
            self.change_state(S.IDLE)
        return spawned

    def _hit_stun(self, cmd: Commands, stage: Stage, has_projectile: bool) -> None:
        if self.y < stage.floor_y or self.vy != 0:
            self._integrate_air(stage)
        if self.state_timer >= self.stun_duration:
            self.change_state(S.FALLING if self.y < stage.floor_y else S.IDLE)

    # ---- combat ---------------------------------------------------------------------------
    def is_blocking(self, hitbox: Hitbox) -> bool:
        """Blocks only when guarding AND the attack comes from the side the fighter faces."""
        if self.state is not S.DEFENDING:
            return False
        side = 1 if hitbox.rect.centerx >= self.x else -1
        return side == self.facing

    def apply_hit(self, event: HitEvent) -> None:
        hit = event.hitbox
        self.push_dir = 1 if self.x >= hit.rect.centerx else -1
        if event.blocked:
            self.push_remaining = hit.knockback // 2
            self.block_lock = hit.blockstun
            return
        self.health = max(0, self.health - hit.damage)
        self.push_remaining = hit.knockback
        self.stun_duration = hit.hitstun
        self.vx = 0
        if self.state is S.HIT_STUN:
            self.state_timer = 0
        else:
            self.change_state(S.HIT_STUN)

    def _apply_push(self) -> None:
        if self.push_remaining > 0:
            step = min(_PUSH_STEP, self.push_remaining)
            self.x += self.push_dir * step
            self.push_remaining -= step

    def _separate(self, opponent: "Fighter", prev_x: float) -> None:
        if not (self.grounded and opponent.grounded):
            return
        min_dist = self.config.hurtbox.w
        if abs(self.x - opponent.x) < min_dist:
            side = 1 if prev_x >= opponent.x else -1
            self.x = opponent.x + side * min_dist

    # ---- boxes ----------------------------------------------------------------------------
    def _hurt_args(self) -> tuple[int, int, int, int]:
        hb = self.config.hurtbox
        return hb.w, hb.h, hb.offset_x, hb.offset_y

    def _refresh_boxes(self) -> None:
        self.hurtbox.rect = place_box(self.x, self.y, self.facing, *self._hurt_args())
        if self.active_hitbox is not None:
            box = self._attack_config().box
            self.active_hitbox.rect = place_box(self.x, self.y, self.facing, box.w, box.h,
                                                box.offset_x, box.offset_y)
