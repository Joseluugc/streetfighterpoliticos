<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Bump rationale: First ratification; every placeholder replaced with concrete governance content.

Modified principles (template slot → new title):
- [PRINCIPLE_1_NAME] → I. Strict Object-Oriented Design & Separation of Concerns
- [PRINCIPLE_2_NAME] → II. Finite State Machine for Character Behavior
- [PRINCIPLE_3_NAME] → III. Separate Hitbox and Hurtbox Collision
- [PRINCIPLE_4_NAME] → IV. 60 FPS Fixed-Timestep Game Loop
- [PRINCIPLE_5_NAME] → V. Spritesheet Slice Management (9-Frame Animations)

Added sections:
- Technical Constraints (was [SECTION_2_NAME])
- Development Workflow & Quality Gates (was [SECTION_3_NAME])
- Governance rules filled in

Removed sections: none

Templates requiring updates:
- .specify/templates/plan-template.md: ⚠ not modified by this command (reads constitution at runtime)
- .specify/templates/spec-template.md: ⚠ not modified by this command (reads constitution at runtime)
- .specify/templates/tasks-template.md: ⚠ not modified by this command (reads constitution at runtime)

Deferred TODOs: none
-->

# StreetFighterVersionPoliticos Constitution

## Core Principles

### I. Strict Object-Oriented Design & Separation of Concerns

- All game code MUST be organized into classes with a single, clearly stated responsibility.
  Module-level mutable state and "god objects" are prohibited.
- Responsibilities MUST be split into distinct layers at minimum: game loop/scene management,
  input handling, fighter logic (state, physics, combat stats), collision/combat resolution,
  rendering, and asset loading.
- Game logic classes (fighter state, physics, combat) MUST NOT call `pygame.display`,
  `pygame.draw`, or blit to surfaces; drawing is the exclusive job of the rendering layer.
- Input MUST be translated into abstract commands (e.g. `MOVE_LEFT`, `PUNCH`) before reaching
  fighter logic, so fighters never read raw key codes.
- Shared behavior MUST be expressed through composition or inheritance from a common base
  (e.g. `Fighter`), never through copy-paste between characters.

**Rationale**: A fighting game grows by adding characters, moves and stages; isolated
responsibilities let each be added or tested without touching unrelated systems.

### II. Finite State Machine for Character Behavior

- Every fighter MUST be driven by an explicit Finite State Machine with at least these states:
  `IDLE`, `WALKING`, `JUMPING`, `FALLING`, `PUNCHING`, `KICKING`, `DEFENDING`, `SPECIAL`.
- States MUST be defined as an enumeration (or state classes) — never as free-form strings or
  ad-hoc boolean flags such as `is_jumping`.
- Each state MUST expose `enter`, `update`, and `exit` behavior and MUST declare which animation
  it plays and whether it is interruptible.
- Allowed transitions MUST be declared explicitly (e.g. a transition table); any transition not
  declared MUST be rejected. Example: `PUNCHING` cannot be cancelled into `WALKING` until its
  animation completes unless the transition is declared.
- The current animation MUST be derived from the current state, never set independently.

**Rationale**: An explicit FSM makes move priority, cancels and lockouts predictable and
debuggable, and prevents contradictory states (e.g. punching and defending simultaneously).

### III. Separate Hitbox and Hurtbox Collision

- Hitboxes (attack payload) and hurtboxes (damage reception) MUST be distinct types and MUST NOT
  share a class or be reused interchangeably.
- A hitbox MUST carry its attack data: owner, damage, knockback, hitstun/blockstun duration, and
  the frames during which it is active. Hitboxes exist only during the active frames of an attack
  state.
- A hurtbox MUST carry no attack data; it only defines where a fighter can be hit, and MAY change
  shape per state (e.g. crouching, jumping).
- Collision resolution MUST only test hitboxes against opposing fighters' hurtboxes — never a
  fighter's own boxes, and never sprite rectangles.
- A single attack instance MUST register at most one hit per target.
- `DEFENDING` MUST be resolved during hit resolution (applying block rules) rather than by
  disabling the hurtbox.
- A debug overlay MUST be available to draw hitboxes and hurtboxes in distinct colors.

**Rationale**: Separating offensive and defensive geometry is what makes hit detection fair,
tunable per move, and independent of sprite art.

### IV. 60 FPS Fixed-Timestep Game Loop

- Game simulation MUST advance in fixed steps of 1/60 s, using an accumulator decoupled from
  rendering.
- The number of simulation steps per rendered frame MUST be capped to prevent a "spiral of
  death" when the machine falls behind.
- All gameplay timings (animation frame duration, attack startup/active/recovery, hitstun,
  jump arcs) MUST be expressed in simulation frames, not in wall-clock seconds.
- Simulation code MUST NOT read wall-clock time or depend on rendering frame rate; given the same
  inputs it MUST produce the same results.
- The game MUST target a stable 60 FPS on the reference development machine; frame-time
  regressions are treated as defects.

**Rationale**: Fighting games depend on frame-exact timing; a fixed timestep keeps gameplay
identical regardless of hardware speed and makes behavior reproducible in tests.

### V. Spritesheet Slice Management (9-Frame Animations)

- Character animations MUST be sourced from spritesheets and sliced into frames by a dedicated
  asset/spritesheet class.
- Each character animation MUST consist of exactly 9 frames, and frame dimensions/layout MUST be
  declared in data (configuration), not hardcoded inside fighter logic.
- Slicing MUST happen once at load time and frames MUST be cached; slicing or loading images
  inside the game loop is prohibited.
- A missing spritesheet, or one whose dimensions do not yield 9 frames per animation, MUST fail
  loudly at load time with a clear error naming the file and animation.
- Each FSM state (Principle II) MUST map to exactly one animation.

**Rationale**: A uniform, data-driven frame layout lets new characters be added by supplying art
and config alone, and load-time validation catches broken assets before a match starts.

## Technical Constraints

- **Language**: Python 3 (3.10 or newer).
- **Framework**: Pygame is the only rendering, input, audio and windowing library.
- **Dependencies**: New third-party runtime dependencies MUST be justified in the feature plan.
  Dependencies MUST be pinned in a requirements file.
- **Assets**: Spritesheets, sounds and fonts MUST live under a dedicated assets directory and be
  loaded only through the asset-loading layer.
- **Configuration**: Tunable gameplay values (damage, speeds, frame data, box geometry) MUST live
  in data/config structures rather than as magic numbers in logic code.
- **Style**: Code MUST follow PEP 8 and use type hints on public classes and methods.

## Development Workflow & Quality Gates

- Each feature MUST go through the Spec Kit flow (specify → plan → tasks → implement), and its
  plan MUST include a Constitution Check against Principles I–V.
- Non-rendering logic (FSM transitions, hitbox/hurtbox resolution, fixed-timestep stepping,
  spritesheet slicing validation) MUST be covered by automated tests (pytest) that run headless
  (e.g. `SDL_VIDEODRIVER=dummy`).
- A change is complete only when: tests pass, the game launches and runs a match without errors,
  and the hitbox/hurtbox debug overlay shows correct geometry for any new or changed move.
- Any deviation from a principle MUST be recorded with its justification in the plan's
  Complexity Tracking section.

## Governance

- This constitution supersedes all other project practices. Where a spec, plan or task conflicts
  with it, the constitution wins until it is formally amended.
- **Amendments** MUST be made via `/speckit-constitution`, MUST include an updated Sync Impact
  Report, and MUST state the reason for the change and any migration needed for existing code.
- **Versioning** follows semantic versioning:
  - MAJOR: removing or redefining a principle in a backward-incompatible way.
  - MINOR: adding a principle or section, or materially expanding guidance.
  - PATCH: clarifications, wording and typo fixes.
- **Compliance**: Every plan and code review MUST verify compliance with the Core Principles;
  unjustified violations block completion of the feature.

**Version**: 1.0.0 | **Ratified**: 2026-11-11 | **Last Amended**: 2026-11-11
