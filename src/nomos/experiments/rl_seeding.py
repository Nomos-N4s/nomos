"""Single seeding entrypoint for the RL adversary experiments (E6, #264).

Reproducibility of the adversary result depends on seeding *every* source of
randomness the pipeline touches from one place, rather than sprinkling seeds ad
hoc. :func:`seed_everything` seeds the Python ``random`` module, NumPy, PyTorch,
and stable-baselines3's own helper.

Determinism caveats (documented, not silently assumed):

- On **CPU**, PPO in stable-baselines3 is deterministic given identical seeds
  *and* identical library versions (see the pinned ``rl-repro`` extra). This is
  the configuration used for the published run.
- On **GPU**, some cuDNN kernels are nondeterministic; bit-exact reproduction is
  not guaranteed there.
- Multi-threaded BLAS can reorder floating-point reductions. Set
  ``OMP_NUM_THREADS=1`` for the strictest reproduction.
- ``PYTHONHASHSEED`` affects set/dict ordering in the parent process and cannot
  be changed after interpreter start; export it before launching Python if hash
  ordering matters.
"""

from __future__ import annotations

import os
import random


def seed_everything(seed: int, *, deterministic_torch: bool = False) -> int:
    """Seed every RNG the RL pipeline uses and return the seed.

    Args:
        seed: The seed to apply to ``random``, NumPy, PyTorch, and
            stable-baselines3.
        deterministic_torch: When ``True``, additionally request deterministic
            PyTorch algorithms (``warn_only`` so unsupported ops degrade to a
            warning rather than raising).

    Returns:
        The seed, so callers can log exactly what was applied.
    """
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)

    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:  # pragma: no cover - numpy is a base dependency
        pass

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():  # pragma: no cover - CI is CPU-only
            torch.cuda.manual_seed_all(seed)
        if deterministic_torch:  # pragma: no cover - opt-in strict mode
            torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:  # pragma: no cover - only when rl extra missing
        pass

    try:
        from stable_baselines3.common.utils import set_random_seed

        set_random_seed(seed)
    except ImportError:  # pragma: no cover - only when rl extra missing
        pass

    return seed


def derive_rng(seed: int, stream: str) -> random.Random:
    """Return a dedicated, deterministic RNG for one named source of randomness.

    Sources of noise that are *part of the experiment* — the verifier's error
    process (V1, #272), for instance — must not be drawn from an RNG that also
    drives something else. Sharing a stream makes the number of draws
    load-bearing: turning noise on would shift the grid layout, and the ε = 1.0
    configuration would stop reproducing the published run. Each stream gets its
    own generator, derived from the run seed so the whole set stays reproducible
    from one number.

    Seeding from a string is deliberate: ``random.Random`` hashes it with SHA-512
    internally, so the derivation is stable across processes and unaffected by
    ``PYTHONHASHSEED``.

    Args:
        seed: The run seed, as passed to :func:`seed_everything`.
        stream: A stable name for the noise source (e.g. ``"verifier"``).

    Returns:
        A :class:`random.Random` private to ``(seed, stream)``.
    """
    return random.Random(f"nomos:{stream}:{seed}")
