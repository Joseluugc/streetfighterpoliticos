"""Entry point: `python -m src.main`."""
from __future__ import annotations

import sys

from src.config.settings import ConfigError
from src.engine.game import Game
from src.utils.spritesheet import SpriteSheetError


def main() -> int:
    try:
        game = Game()
    except (SpriteSheetError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
