# Tasks: "Rude Politic" Fighter & "Golpe Español"

- [X] T001 Analyse repo (game = `index.html`, select = `ui/character-select/`, pygame engine untouched)
- [X] T002 Analyse `assets/rudepolitic.png` (5 strips: 6/5/5/5/5 poses; labels; touching poses; interior grays)
- [X] T003 Write spec, plan, tasks (`specs/002-rude-politic-fighter/`)
- [X] T004 `scripts/build_rudepolitic_atlas.py` -> `assets/characters/rudepolitic.png` + frames in JSON
- [X] T005 Author `assets/characters/rudepolitic.json` (animations, hurtbox, attacks, special, scale)
- [X] T006 Tests first: `tests/unit/test_rudepolitic_atlas.py` (SC-1..SC-4)
- [X] T007 Engine: `DEFAULT_CHAR` + `CHAR_DEFS` + definition loader (fetch JSON, load atlas, skip on error)
- [X] T008 Engine: `Fighter.char`, per-char hurtbox/attacks/scale/walk speed; `animFrame()` replacing `frameIndex`
- [X] T009 Engine: jump phases + landing frame (`landT`)
- [X] T010 Engine: melee special state, `slamImpact()` effects, trail, banner, `Sound.slam`, clash opt-out
- [X] T011 Select screen: roster entry, per-character portrait, "Especial: ..." line, 5-tile grid
- [X] T012 Headless-browser end-to-end run (every move, damage numbers, console errors)
- [X] T013 Regression: full pytest suite + default fighters' behaviour
- [X] T014 Final polish: hitbox tuning with debug boxes, docs
