"""Translate raw keyboard state into abstract fighter commands."""
from __future__ import annotations

from dataclasses import dataclass, replace

from src.config.settings import KeyScheme


@dataclass(frozen=True, slots=True)
class Commands:
    left: bool = False
    right: bool = False
    jump: bool = False
    punch: bool = False
    kick: bool = False
    guard: bool = False
    special: bool = False

    def resolved(self) -> "Commands":
        """Apply edge-case rules: left+right cancel; one action wins by priority.

        Priority: guard > special > kick > punch > jump > walk.
        """
        cmd = self
        if cmd.left and cmd.right:
            cmd = replace(cmd, left=False, right=False)
        winner = next((n for n in ("guard", "special", "kick", "punch", "jump") if getattr(cmd, n)), None)
        return replace(cmd, **{n: n == winner for n in ("guard", "special", "kick", "punch", "jump")})


class InputMapper:
    """Reads a pygame key-state sequence; fighters never see key codes."""

    @staticmethod
    def read(keys, scheme: KeyScheme) -> Commands:
        return Commands(left=bool(keys[scheme.left]), right=bool(keys[scheme.right]),
                        jump=bool(keys[scheme.jump]), punch=bool(keys[scheme.punch]),
                        kick=bool(keys[scheme.kick]), guard=bool(keys[scheme.guard]),
                        special=bool(keys[scheme.special]))

    @staticmethod
    def read_training(keys, scheme: KeyScheme) -> Commands:
        """Debug controls for the training dummy."""
        return Commands(punch=bool(keys[scheme.training_punch]), kick=bool(keys[scheme.training_kick]),
                        guard=bool(keys[scheme.training_guard]),
                        special=bool(keys[scheme.training_special]))
