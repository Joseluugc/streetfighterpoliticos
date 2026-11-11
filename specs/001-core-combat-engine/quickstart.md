# Quickstart: Core Combat Engine & Dummy Character

Validation guide to prove the feature works end to end. Details of types and signatures are in
[data-model.md](data-model.md) and [contracts/module-interfaces.md](contracts/module-interfaces.md).

## Prerequisites

- Python 3.10+ and `pip`
- A 3x3 grid PNG at `assets/characters/dummy.png` (placeholder with numbered frames 1-9 is fine)

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # pygame, pytest (pinned)
```

## Automated validation (headless)

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest -q
```

Expected: all unit and integration tests pass, covering:

| Area | Proves |
|------|--------|
| spritesheet | 9 frames sliced, bad size/missing file fails with file name (FR-001, FR-002) |
| fsm | Only declared transitions allowed; frame matches state (FR-004) |
| idle | Frames 1/2 alternate every 30 updates (FR-003, SC-002) |
| movement | Walk, bounds, jump arc identical every time, no double jump (FR-007..010, SC-004) |
| physics | Hit once, no self-hit, miss, behind-hit not blocked (FR-014..018, SC-005) |
| projectile | Spawns at update 12, moves, dies on hit/edge/90 updates (FR-020..023, SC-007) |
| timestep | Accumulator runs N updates for N/60 s, capped at 5 per frame (FR-006) |

## Manual validation (real window)

```bash
python -m src.main
```

| Step | Expected |
|------|----------|
| Do nothing for 5 s | Dummy alternates frame 1 / frame 2 every 0.5 s |
| Hold D / A, tap W | Frame 3 while walking; frame 4 rising, frame 5 falling; lands at floor |
| Walk next to training dummy, press J then K | Frame 6 / 7; its health bar drops by 5 / 8 once per attack |
| Press F1 | Hitboxes, hurtboxes and projectile boxes appear in distinct colors |
| Press 3 (training dummy guards), then J | No damage; small push-back |
| Press I | Frame 9; projectile appears after ~0.2 s, travels forward, vanishes on hit or after 1.5 s |
| Press I again while projectile visible | Nothing happens |
| Rename `dummy.png` and relaunch | Game refuses to start with an error naming the file |

## Success check

All automated tests pass and every manual row behaves as expected, matching SC-001 to SC-007 in
[spec.md](spec.md).
