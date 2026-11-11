# Feature Specification: Core Combat Engine & Dummy Character

**Feature Branch**: `001-core-combat-engine`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Create the initial spec for the Core Combat Engine and Dummy Character.
Define user stories and acceptance criteria for: 1. Frame animation loop for Standby/Idle state
(alternating frames 1 & 2). 2. Horizontal walking movement (frame 3) and Jump/Fall gravity physics
(frames 4 & 5). 3. Basic Melee Combat: Punch (frame 6), Kick (frame 7), and Guard/Block (frame 8).
4. Special Move ("Ley de Vivienda"): Frame 9 activation spawning a forward-moving projectile entity
with its own bounding box and lifetime."

## Overview

This feature delivers the first playable slice of the game: a single generic **Dummy Character**
that a player controls on one flat stage, facing a second, uncontrolled Dummy used as a training
target. The Dummy proves out the shared combat engine every future character will reuse: idle
animation, movement, jumping, melee attacks, guarding, and one projectile special move.

Every Dummy pose comes from one 9-frame character sheet with this fixed mapping:

| Frame | Pose | Used by state |
|-------|------|---------------|
| 1, 2 | Standby (alternating) | Idle |
| 3 | Walk | Walking |
| 4 | Jump (rising) | Jumping |
| 5 | Fall (descending) | Falling |
| 6 | Punch | Punching |
| 7 | Kick | Kicking |
| 8 | Guard | Defending |
| 9 | Special cast | Special ("Ley de Vivienda") |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Character stands in a living Idle pose (Priority: P1)

When a match starts, the player sees the Dummy standing on the stage floor, gently "breathing"
by alternating between Standby frames 1 and 2 at a steady rhythm while no input is given.

**Why this priority**: It is the minimum visible proof that the character sheet loads, frames are
sliced correctly, and the game updates on a steady clock. Every other state returns to Idle.

**Independent Test**: Launch the game and press nothing. The Dummy alternates frames 1 and 2 at a
constant rhythm, indefinitely, without drift or flicker.

**Acceptance Scenarios**:

1. **Given** a match has just started, **When** no input is pressed, **Then** the Dummy is shown
   on the floor in Idle, displaying frame 1.
2. **Given** the Dummy is Idle, **When** 30 game updates (0.5 s) have elapsed, **Then** the
   displayed frame switches from 1 to 2, and after another 30 updates switches back to 1.
3. **Given** the Dummy is Idle for 60 seconds, **When** the frame sequence is observed, **Then** it
   only ever shows frames 1 and 2, alternating every 0.5 s with no other frame appearing.
4. **Given** any other action (walk, landing, attack, guard, special) finishes, **When** no input
   is held, **Then** the Dummy returns to Idle and restarts the cycle at frame 1.

---

### User Story 2 - Walk, jump and fall under gravity (Priority: P2)

The player moves the Dummy left and right across the stage (showing the Walk pose, frame 3) and
makes it jump. While rising it shows the Jump pose (frame 4); once it starts coming down it shows
the Fall pose (frame 5) until it lands back on the floor.

**Why this priority**: Movement and spacing are the foundation of any fighting game; combat in
later stories depends on fighters being able to approach, retreat and jump.

**Independent Test**: Hold left/right and press jump on an empty stage. The Dummy moves at
constant speed, stops at stage edges, follows a smooth arc when jumping, and shows the correct
frame in each phase.

**Acceptance Scenarios**:

1. **Given** the Dummy is Idle, **When** the player holds Right, **Then** the Dummy moves right at a
   constant speed and displays frame 3 for as long as Right is held.
2. **Given** the Dummy is walking, **When** the player releases the direction, **Then** the Dummy
   stops on the next update and returns to Idle.
3. **Given** the Dummy is at the left or right stage boundary, **When** the player holds toward
   that boundary, **Then** the Dummy stays inside the stage.
4. **Given** the Dummy is on the floor, **When** the player presses Jump, **Then** the Dummy
   leaves the floor upward, displays frame 4 while rising, and the jump cannot be repeated until
   it lands (no double jump).
5. **Given** the Dummy is rising, **When** its upward speed reaches zero at the jump apex,
   **Then** it switches to Falling, displays frame 5, and accelerates downward until it lands.
6. **Given** the Dummy jumps while holding a direction, **When** it is airborne, **Then** it keeps
   the horizontal direction it had at take-off and cannot change direction mid-air.
7. **Given** the Dummy is falling, **When** it touches the floor, **Then** it stops at floor
   level exactly (never below it) and returns to Idle, or Walking if a direction is held.
8. **Given** the same jump input is performed twice, **When** both jumps are measured, **Then**
   they reach the same peak height and last the same number of updates.

---

### User Story 3 - Punch, kick and guard against an opponent (Priority: P3)

The player punches (frame 6) or kicks (frame 7) the training Dummy to deal damage, and holds
Guard (frame 8) to block incoming attacks. A visible health value for each fighter shows the
effect of hits.

**Why this priority**: Melee combat is the core interaction of the genre and the first time two
fighters affect each other. It depends on Idle and movement being in place.

**Independent Test**: Place the player Dummy next to the training Dummy and attack it; then make
the training Dummy attack (via a debug trigger) while the player holds Guard. Health changes and
blocks behave as specified, and an optional debug overlay shows attack and damage areas.

**Acceptance Scenarios**:

1. **Given** the Dummy is Idle or Walking on the floor, **When** the player presses Punch,
   **Then** it shows frame 6 for the full punch duration and cannot walk, jump or start another
   action until the punch finishes.
2. **Given** the Dummy is Idle or Walking on the floor, **When** the player presses Kick, **Then**
   it shows frame 7 for the full kick duration, which is longer and reaches farther than the
   punch, and deals more damage.
3. **Given** the opponent is within punch range in front of the attacker, **When** the punch
   reaches its active moment, **Then** the opponent loses punch damage once, briefly flinches
   (hit stun) and is pushed back slightly.
4. **Given** the opponent is out of range or behind the attacker, **When** a punch or kick is
   performed, **Then** the opponent takes no damage.
5. **Given** a single punch or kick overlaps the opponent for several updates, **When** the
   attack finishes, **Then** the opponent was damaged exactly once by it.
6. **Given** the Dummy is on the floor, **When** the player holds Guard, **Then** it shows
   frame 8, does not move, and stays guarding for as long as Guard is held.
7. **Given** the Dummy is guarding and facing the attacker, **When** a punch, kick or projectile
   hits it, **Then** it loses no health, is pushed back slightly, and stays in Guard.
8. **Given** the Dummy is guarding, **When** an attack lands from behind, **Then** the block fails
   and full damage is taken.
9. **Given** the Dummy is hit while Idle, Walking or attacking, **When** the hit lands, **Then**
   any attack in progress is interrupted.

---

### User Story 4 - Special move "Ley de Vivienda" projectile (Priority: P4)

The player performs the special move "Ley de Vivienda": the Dummy shows its cast pose (frame 9)
and launches a projectile that travels forward across the stage on its own, damaging the
opponent if it connects, and disappearing when it hits something, leaves the stage, or its
lifetime runs out.

**Why this priority**: It introduces independent entities that live apart from the fighter,
the template for every future character's signature move. It builds on all previous stories.

**Independent Test**: Trigger the special on an empty stage and watch the projectile cross and
vanish; then trigger it at the training Dummy (guarding and not guarding) and check damage.

**Acceptance Scenarios**:

1. **Given** the Dummy is Idle or Walking on the floor and has no projectile on screen, **When**
   the player presses Special, **Then** it shows frame 9 for the full cast duration and is locked
   out of other actions until the cast ends.
2. **Given** the cast is in progress, **When** the cast reaches its release moment, **Then** one
   "Ley de Vivienda" projectile appears just in front of the Dummy at chest height and moves
   horizontally in the direction the Dummy faces at constant speed.
3. **Given** a projectile is travelling, **When** the Dummy that fired it moves, jumps or is hit,
   **Then** the projectile keeps travelling unaffected.
4. **Given** a projectile overlaps the opponent's damage area, **When** the overlap occurs,
   **Then** the opponent takes special damage once (or is blocked per Story 3 if guarding while
   facing it) and the projectile disappears immediately.
5. **Given** a projectile hits nothing, **When** it leaves the stage or its lifetime of
   90 updates (1.5 s) expires, **Then** it disappears.
6. **Given** the Dummy already has a projectile on screen, **When** the player presses Special,
   **Then** nothing happens (no cast, no new projectile).
7. **Given** a projectile overlaps the fighter that fired it, **When** the overlap occurs,
   **Then** that fighter takes no damage.

### Edge Cases

- Several action buttons pressed on the same update: one wins by fixed priority
  (Guard > Special > Kick > Punch > Jump > Walk).
- Left and Right held at the same time: the Dummy stays still (Idle).
- Attack, Guard or Special pressed mid-air: ignored; aerial actions are out of scope.
- Both fighters hit each other on the same update: both take damage (a trade).
- Fighters walk into each other: they cannot pass through or overlap; one blocks the other.
- One fighter jumps over the other: both turn to keep facing each other once the jumper lands.
- A fighter's health reaches zero: health stays at zero and is not reduced further; no
  knockout sequence or round end happens in this feature.
- Two opposing projectiles meet: they pass through each other; projectile clashes are out of
  scope.
- The character sheet is missing or does not contain exactly 9 frames: the game refuses to start
  and shows an error naming the file.
- The game window is moved or the machine stalls briefly: gameplay does not speed up or skip
  logic steps unpredictably; timings measured in updates stay identical.

## Requirements *(mandatory)*

### Functional Requirements

**Animation & character sheet**

- **FR-001**: The game MUST load the Dummy's appearance from a single character sheet of exactly
  9 frames and use the frame-to-pose mapping defined in the Overview table.
- **FR-002**: The game MUST refuse to start, with an error naming the file, if the sheet is
  missing or does not divide into 9 frames.
- **FR-003**: In Idle, the Dummy MUST alternate between frames 1 and 2 every 30 updates.
- **FR-004**: Each state MUST display only its assigned frame(s); the displayed frame MUST always
  match the current state.
- **FR-005**: The Dummy MUST be drawn mirrored when facing left, so both fighters can face each
  other using the same sheet.

**Timing**

- **FR-006**: Game logic MUST advance in fixed steps of 60 updates per second, independent of
  how fast frames are drawn, and all durations in this spec MUST be measured in updates.

**Movement & physics**

- **FR-007**: The player MUST be able to walk the Dummy left and right at a constant speed, with
  the Dummy confined to the stage boundaries.
- **FR-008**: The player MUST be able to jump only when on the floor; the jump MUST follow a
  consistent arc under constant gravity, with Jumping (frame 4) while rising and Falling
  (frame 5) while descending.
- **FR-009**: Horizontal direction during a jump MUST be fixed at take-off.
- **FR-010**: On landing, the Dummy MUST rest exactly at floor level and return to Idle, or to
  Walking if a direction is held.
- **FR-011**: The two fighters MUST NOT overlap or pass through each other on the ground, and
  MUST automatically face each other whenever both are on the floor.

**Melee combat**

- **FR-012**: The player MUST be able to Punch (frame 6) and Kick (frame 7) only while on the
  floor and not already busy with another action.
- **FR-013**: Each attack MUST have three phases: a short wind-up, an active period during which
  it can hit, and a recovery; the attacker MUST NOT be able to act until recovery ends.
- **FR-014**: Each attack MUST define an attack area that exists only during its active period;
  each fighter MUST have a separate damage-receiving area. An attack hits only when its attack
  area overlaps the *opponent's* damage-receiving area.
- **FR-015**: Each attack instance MUST damage a given opponent at most once.
- **FR-016**: A successful hit MUST reduce the opponent's health by the attack's damage, apply hit
  stun, push the opponent back, and interrupt any action the opponent was performing.
- **FR-017**: The player MUST be able to Guard (frame 8) while on the floor by holding the Guard
  input; the Dummy MUST stay still while guarding.
- **FR-018**: A hit on a guarding fighter that faces the attacker MUST deal no damage and apply a
  short block push-back; a hit from behind MUST NOT be blocked.
- **FR-019**: Each fighter MUST have a health value, shown on screen, starting at 100 and never
  going below 0.

**Special move "Ley de Vivienda"**

- **FR-020**: The player MUST be able to trigger "Ley de Vivienda" with a dedicated Special input
  while on the floor, not busy, and with no own projectile on screen.
- **FR-021**: The special MUST display frame 9 during its cast and release exactly one projectile
  at a fixed moment of the cast.
- **FR-022**: The projectile MUST be an independent object with its own position, constant forward
  speed in the caster's facing direction, its own hit area, damage value, owner, and a lifetime
  of 90 updates.
- **FR-023**: The projectile MUST disappear when it hits the opponent (damaging or being blocked),
  leaves the stage, or its lifetime ends, and MUST never damage its owner.

**Controls & debugging**

- **FR-024**: The player MUST control the Dummy with keyboard inputs for Left, Right, Jump, Punch,
  Kick, Guard and Special, resolved by the priority order listed in Edge Cases.
- **FR-025**: The training Dummy MUST be uncontrolled by default (standing Idle), and a debug
  control MUST make it perform a punch, kick, guard or special on demand so blocking and
  damage-taking can be tested.
- **FR-026**: A toggleable debug overlay MUST draw each fighter's damage-receiving area, active
  attack areas and projectile areas in clearly distinct colors.

### Default Gameplay Values

These starting values make requirements testable; they are expected to be tuned during play-testing.

| Action | Wind-up | Active | Recovery | Damage | Reach |
|--------|---------|--------|----------|--------|-------|
| Punch | 4 updates | 3 updates | 8 updates | 5 | Short |
| Kick | 7 updates | 4 updates | 12 updates | 8 | Longer than punch |
| Special cast | 12 updates (projectile released) | — | 18 updates | 10 (projectile) | Full stage |

- Hit stun: 15 updates. Block push-back stun: 8 updates.
- Projectile lifetime: 90 updates; one per fighter on screen at a time.

### Key Entities

- **Fighter (Dummy)**: A character on the stage. Has position, velocity, facing direction, health
  (0-100), current state, its damage-receiving area, and its character sheet. Two exist: the
  player-controlled Dummy and the training Dummy.
- **Character State**: One of Idle, Walking, Jumping, Falling, Punching, Kicking, Defending,
  Special, plus Hit Stun as the reaction to being hit. Determines which frame is shown, what
  actions are allowed, and how long the state lasts.
- **Character Sheet**: The 9-frame image set for a character plus its frame-to-pose mapping.
- **Attack Area (hitbox)**: A temporary region carrying owner, damage, push-back and stun, active
  only during an attack's active period.
- **Damage-Receiving Area (hurtbox)**: The region where a fighter can be hit; carries no attack data.
- **Projectile ("Ley de Vivienda")**: Independent moving object with position, speed, direction,
  owner, attack area, damage and remaining lifetime.
- **Stage**: Flat floor with left and right boundaries that contains fighters and projectiles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The game holds a steady 60 updates per second during a 5-minute session with both
  fighters and projectiles active, with no visible stutter on the reference machine.
- **SC-002**: Over 60 seconds of Idle, the frame shown alternates between frames 1 and 2 exactly
  every 0.5 s (±1 update), and no other frame appears.
- **SC-003**: In 100% of observed states, the frame shown matches the Overview mapping.
- **SC-004**: Ten consecutive identical jumps all reach the same peak height and take the same
  number of updates from take-off to landing.
- **SC-005**: Across 50 test attacks, each punch, kick or projectile that connects deals its
  damage exactly once, and no attack that misses or hits a correctly facing guard deals damage.
- **SC-006**: A first-time player, given the control list, can walk, jump, punch, kick, guard and
  fire "Ley de Vivienda" within 2 minutes of starting.
- **SC-007**: Every projectile disappears within 1.5 s of being fired, or immediately on hitting
  the opponent.

## Assumptions

- The **Dummy Character** is a generic placeholder fighter used to build and validate the engine;
  political-figure characters come in later features and reuse the same engine and frame layout.
- One player on a keyboard controls one Dummy; the second Dummy is a training target with debug
  triggers. Two-player local play, AI opponents, menus, rounds, timers, KO sequences, sound,
  combos, crouching, aerial attacks and projectile clashes are out of scope.
- Each animated state uses a single frame from the 9-frame sheet (Idle uses two). The project
  constitution's Principle V says "each character animation MUST consist of exactly 9 frames";
  this spec interprets it as "each character has exactly one 9-frame sheet", which should be
  confirmed or the constitution amended.
- Punch, kick, guard and special are ground-only actions.
- Gameplay values above are starting values and can be tuned without changing this spec.
- A Dummy character sheet with 9 frames will be supplied; until real art exists, a simple
  placeholder sheet with numbered frames is acceptable.
- Default keys: A/D move, W jump, J punch, K kick, L guard, I special; F1 toggles the debug
  overlay. Exact key choices can change without changing this spec.
