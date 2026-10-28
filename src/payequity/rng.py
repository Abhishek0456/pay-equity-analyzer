"""Part 1 — Seeded RNG factory: one numpy Generator per generation stage, derived from the
master seed so that adding a stage never changes another stage's random stream.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _stage_key(stage: str) -> int:
    # Stable across processes/platforms (unlike built-in hash(), which is salted per run).
    return int.from_bytes(hashlib.sha256(stage.encode("utf-8")).digest()[:8], "big")


def stage_rng(seed: int, stage: str) -> np.random.Generator:
    """Independent, reproducible Generator for a named stage, e.g. stage_rng(seed, "bands")."""
    return np.random.default_rng(np.random.SeedSequence(entropy=seed, spawn_key=(_stage_key(stage),)))


class RngFactory:
    """Hands out per-stage generators for one master seed; asking twice for a stage restarts its stream."""

    def __init__(self, seed: int):
        self.seed = seed

    def __call__(self, stage: str) -> np.random.Generator:
        return stage_rng(self.seed, stage)
