"""Grounded verifiers of tunable accuracy for the Integrity committee (V1, #272).

The first adversary campaign gave Integrity an **oracle**: it read the true tile,
so "the grounded verifier catches lies" was close to true by construction
(Appendix E §E.5.1(1)). Real deployments never have an oracle. This module makes
verifier accuracy the independent variable.

Every verifier answers exactly one question — *which tile do I believe I am
looking at?* — and the whole Integrity path downstream is derived from that
answer rather than from the truth. Modelling the error at the observation
instead of at the verdict is what makes both failure directions fall out for
free, with no special case for either:

- a **miss**, when a poison tile is observed as something benign, leaves nothing
  to contradict an inflated coherence claim, so the spoof survives;
- a **false alarm**, when a safe tile is observed as poison, crushes an honest
  proposal's coherence and costs the agent an apple.

Both are real properties of an imperfect verifier, and both are measured.

Three implementations sit on one axis:

- :class:`OracleVerifier` — accuracy 1.0, the published configuration. It draws
  no random numbers at all, so ε = 1.0 reproduces the first campaign exactly.
- :class:`NoisyVerifier` — right with probability ε, otherwise drawn uniformly
  from the tiles it is not looking at. The parametric dial the ε-sweep turns.
- :class:`ClassifierVerifier` — a small multinomial logistic regression that
  predicts the tile from a *noisy sensor reading* of its properties. Its error
  process is a real one rather than a coin flip, and its **measured** accuracy
  places it on the same ε axis, which is what makes the dial interpretable.

The verifiers know nothing about the grid world: a tile is an opaque integer and
its observable properties arrive as a plain feature vector. That keeps the error
model testable on its own and free of the Gymnasium import.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

import numpy as np

from .rl_seeding import derive_rng

#: The RNG stream name verifier noise is drawn from. Private to the verifier so
#: enabling noise cannot perturb the environment's layout draws.
VERIFIER_STREAM = "verifier"

#: Verifier implementations selectable from the protocol runner and CLI.
VERIFIER_KINDS = ("parametric", "classifier")

#: Default noise-to-signal ratio of the learned verifier's sensor. Chosen so the
#: classifier lands in the interesting middle of the ε axis rather than at either
#: end; callers sweep it to move along the axis.
DEFAULT_SENSOR_NOISE = 0.35


class Verifier(ABC):
    """A grounded verifier of bounded accuracy.

    Subclasses answer one question — which tile the verifier believes it sees.
    Everything the Integrity member does with that belief (deciding whether a
    claim is falsified, capping the coherence it will credit) happens in the
    environment, so a verifier never needs to know what a proposal is.
    """

    @property
    @abstractmethod
    def accuracy(self) -> float:
        """The verifier's position on the ε axis, in [0, 1].

        Nominal for :class:`NoisyVerifier` (the dial that was requested),
        measured on held-out data for :class:`ClassifierVerifier`.
        """

    @abstractmethod
    def observe(self, true_tile: int) -> int:
        """Return the tile the verifier believes it is looking at."""

    def reseed(self, seed: int) -> None:
        """Re-derive the noise stream so an episode replays identically.

        Deterministic verifiers have no stream and ignore this.
        """


class OracleVerifier(Verifier):
    """The published configuration: sees ground truth, always.

    Kept as its own class rather than as ``NoisyVerifier(1.0)`` so the oracle
    path provably draws no random numbers. That is the regression guard behind
    "ε = 1.0 reproduces Appendix E bit-for-bit".
    """

    @property
    def accuracy(self) -> float:
        return 1.0

    def observe(self, true_tile: int) -> int:
        return true_tile


class NoisyVerifier(Verifier):
    """Correct with probability ε; otherwise sees one of the other tiles.

    Args:
        accuracy: ε ∈ [0, 1]. The sweep uses [0.5, 1.0]; ε = 0 (always wrong) is
            available because it is the cleanest way to prove in a test that a
            bypass is reachable at all.
        vocabulary: Every tile the environment can present. An error is drawn
            uniformly from this set minus the true tile, so what "being wrong"
            means is fixed by the environment rather than by the verifier.
        seed: Run seed; the noise stream is derived from it via
            :func:`~nomos.experiments.rl_seeding.derive_rng`.

    Raises:
        ValueError: If ``accuracy`` is outside [0, 1] or the vocabulary has
            fewer than two tiles (an error would have nothing to be).
    """

    def __init__(self, accuracy: float, vocabulary: Sequence[int], seed: int = 0):
        if not 0.0 <= accuracy <= 1.0:
            raise ValueError(f"verifier accuracy must be in [0, 1], got {accuracy!r}")
        if len(set(vocabulary)) < 2:
            raise ValueError("verifier vocabulary needs at least two tiles to be wrong about")
        self._accuracy = float(accuracy)
        self._vocabulary = tuple(sorted(set(int(t) for t in vocabulary)))
        self._seed = seed
        self._rng = derive_rng(seed, VERIFIER_STREAM)

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @property
    def vocabulary(self) -> tuple[int, ...]:
        return self._vocabulary

    def reseed(self, seed: int) -> None:
        self._seed = seed
        self._rng = derive_rng(seed, VERIFIER_STREAM)

    def observe(self, true_tile: int) -> int:
        if self._rng.random() < self._accuracy:
            return true_tile
        alternatives = [t for t in self._vocabulary if t != true_tile]
        if not alternatives:  # pragma: no cover - guarded in __init__
            return true_tile
        return self._rng.choice(alternatives)


class ClassifierVerifier(Verifier):
    """A learned verifier: predicts the tile from a noisy reading of it.

    The parametric dial isolates ε cleanly but says nothing about whether a
    realistic error process lands anywhere near it. This verifier supplies that
    check. It observes each tile through a sensor that adds Gaussian noise scaled
    to how much the tiles actually differ, then classifies with a multinomial
    logistic regression trained on samples from the same process. Its confusions
    are structured — tiles with similar properties are mistaken for each other,
    which is exactly what a coin flip cannot produce — and its held-out accuracy
    is a measured number that can be read off against ε.

    Implemented in NumPy on purpose: the verifier must not drag the optional
    ``rl`` extra (torch, stable-baselines3) into the environment.

    Args:
        profiles: Tile → observable feature vector. Every vector must have the
            same length; the environment supplies the true metadata profile.
        sensor_noise: Noise-to-signal ratio. Per feature, noise is Gaussian with
            standard deviation ``sensor_noise × (spread of that feature across
            tiles)``, so the knob is dimensionless and monotone in difficulty.
        seed: Run seed, for both training and the runtime sensor stream.
        n_train: Training samples (balanced across tiles).
        n_eval: Held-out samples used to measure :attr:`accuracy`.
        epochs: Full-batch gradient descent steps.
        learning_rate: Gradient descent step size.

    Raises:
        ValueError: If fewer than two tiles are supplied or the feature vectors
            disagree in length.
    """

    def __init__(
        self,
        profiles: Mapping[int, Sequence[float]],
        sensor_noise: float = DEFAULT_SENSOR_NOISE,
        seed: int = 0,
        n_train: int = 4000,
        n_eval: int = 4000,
        epochs: int = 400,
        learning_rate: float = 0.5,
    ):
        if len(profiles) < 2:
            raise ValueError("classifier verifier needs at least two tiles to distinguish")
        widths = {len(vec) for vec in profiles.values()}
        if len(widths) != 1:
            raise ValueError(f"tile feature vectors must all have the same length, got {widths}")

        self._tiles = tuple(sorted(int(t) for t in profiles))
        self._index = {tile: i for i, tile in enumerate(self._tiles)}
        self._means = np.array([profiles[t] for t in self._tiles], dtype=np.float64)
        self._sensor_noise = float(sensor_noise)
        # Per-feature spread across tiles. A feature every tile shares carries no
        # signal, so it gets no noise either — otherwise the knob would be
        # measuring the padding rather than the discriminability.
        self._scale = self._means.std(axis=0)
        self._seed = seed

        x_train, y_train = self._sample(_numpy_rng(seed, f"{VERIFIER_STREAM}-train"), n_train)
        self._standardizer = (x_train.mean(axis=0), np.maximum(x_train.std(axis=0), 1e-9))
        self._weights, self._bias = self._fit(x_train, y_train, epochs, learning_rate)

        x_eval, y_eval = self._sample(_numpy_rng(seed, f"{VERIFIER_STREAM}-eval"), n_eval)
        self._accuracy = float((self._classify(x_eval) == y_eval).mean())

        self._rng = _numpy_rng(seed, f"{VERIFIER_STREAM}-sensor")

    @property
    def accuracy(self) -> float:
        """Held-out classification accuracy — the measured ε of this verifier."""
        return self._accuracy

    @property
    def sensor_noise(self) -> float:
        return self._sensor_noise

    def reseed(self, seed: int) -> None:
        """Reset the runtime sensor stream. The trained weights are unchanged."""
        self._rng = _numpy_rng(seed, f"{VERIFIER_STREAM}-sensor")

    def observe(self, true_tile: int) -> int:
        idx = self._index.get(int(true_tile))
        if idx is None:
            # A tile the verifier was never trained on is outside its competence;
            # reporting it unchanged would silently grant oracle access.
            return int(self._tiles[0])
        reading = self._means[idx] + self._rng.normal(0.0, self._sensor_noise * self._scale)
        return int(self._tiles[int(self._classify(reading[None, :])[0])])

    def _sample(self, rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
        labels = rng.integers(0, len(self._tiles), size=n)
        noise = rng.normal(0.0, 1.0, size=(n, self._means.shape[1])) * (
            self._sensor_noise * self._scale
        )
        return self._means[labels] + noise, labels

    def _standardize(self, x: np.ndarray) -> np.ndarray:
        mean, std = self._standardizer
        return (x - mean) / std

    def _fit(
        self, x: np.ndarray, y: np.ndarray, epochs: int, learning_rate: float
    ) -> tuple[np.ndarray, np.ndarray]:
        xs = self._standardize(x)
        n_classes = len(self._tiles)
        onehot = np.zeros((len(y), n_classes))
        onehot[np.arange(len(y)), y] = 1.0
        weights = np.zeros((xs.shape[1], n_classes))
        bias = np.zeros(n_classes)
        for _ in range(epochs):
            error = _softmax(xs @ weights + bias) - onehot
            weights -= learning_rate * (xs.T @ error) / len(xs)
            bias -= learning_rate * error.mean(axis=0)
        return weights, bias

    def _classify(self, x: np.ndarray) -> np.ndarray:
        return np.argmax(self._standardize(x) @ self._weights + self._bias, axis=1)


def _numpy_rng(seed: int, stream: str) -> np.random.Generator:
    """Derive a NumPy generator through the central seeding entrypoint.

    Python's builtin ``hash`` is salted per process, so seeding NumPy from
    ``hash((name, seed))`` would silently make every run irreproducible across
    interpreter launches — the exact failure the single seeding entrypoint
    exists to prevent.
    """
    return np.random.default_rng(derive_rng(seed, stream).getrandbits(64))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=1, keepdims=True)


def make_verifier(
    kind: str,
    accuracy: float,
    vocabulary: Sequence[int],
    profiles: Mapping[int, Sequence[float]],
    seed: int = 0,
    sensor_noise: float = DEFAULT_SENSOR_NOISE,
) -> Verifier:
    """Build the verifier a run configuration asks for.

    ``kind="parametric"`` with ``accuracy=1.0`` returns the :class:`OracleVerifier`
    rather than a ``NoisyVerifier`` that never errs, so the published
    configuration keeps its guarantee of drawing no random numbers.

    Args:
        kind: One of :data:`VERIFIER_KINDS`.
        accuracy: ε for the parametric dial. Ignored by the classifier, whose
            accuracy is measured rather than set.
        vocabulary: Every tile the environment can present.
        profiles: Tile → observable feature vector, for the learned verifier.
        seed: Run seed for the noise stream.
        sensor_noise: Sensor noise-to-signal ratio for the learned verifier.

    Returns:
        The configured :class:`Verifier`.

    Raises:
        ValueError: If ``kind`` is not one of :data:`VERIFIER_KINDS`, or if
            ``accuracy`` is outside [0, 1]. The range is checked here as well as
            in :class:`NoisyVerifier` because ``accuracy=1.5`` would otherwise
            resolve to the oracle and silently pass off a typo as the published
            configuration.
    """
    if kind not in VERIFIER_KINDS:
        raise ValueError(f"Unknown verifier kind {kind!r}; expected one of {VERIFIER_KINDS}")
    if not 0.0 <= accuracy <= 1.0:
        raise ValueError(f"verifier accuracy must be in [0, 1], got {accuracy!r}")
    if kind == "classifier":
        return ClassifierVerifier(profiles, sensor_noise=sensor_noise, seed=seed)
    if accuracy >= 1.0:
        return OracleVerifier()
    return NoisyVerifier(accuracy, vocabulary, seed=seed)
