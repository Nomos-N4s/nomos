"""
Flat-branch and fixed-iteration helpers for constant-time execution (Appendix A §10).

These helpers keep their control flow and memory-access pattern independent
of the sensitive values they touch - the data-oblivious *discipline* a real
TEE deployment would need against cache-timing side channels. As pure Python
they are an executable specification of that discipline, not a defence:
CPython makes no constant-cycle guarantee, and nothing in the governance
path calls these helpers (#311).

In a TEE context, timing side channels can leak information about:
- Which actions were vetoed (via comparison timing)
- Which committee members voted which way
- The identity coherence threshold

Each function here is designed to be data-oblivious: the control flow and
memory access pattern do not depend on sensitive values.

Real-world analogy:
    A judge who takes exactly the same time to read every verdict,
    regardless of whether it is guilty or not guilty. Observers cannot
    infer the outcome from the judge's reading speed.
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def cmov(condition: bool, a: T, b: T) -> T:
    """Branchless-selection pattern: both paths are always computed.

    Returns ``a`` if ``condition`` is True, ``b`` otherwise. This is the
    *pattern* of a constant-time conditional move, not a timing guarantee:
    the mask derivation below is itself a Python branch, and CPython's
    interpreter gives no constant-cycle behaviour either way (#311). In a
    compiled implementation this shape is what keeps the branch predictor
    blind to the condition.

    Args:
        condition: The selection condition.
        a: Value returned if condition is True.
        b: Value returned if condition is False.

    Returns:
        ``a`` or ``b`` based on ``condition``.
    """
    mask = 1 if condition else 0
    return a * mask + b * (1 - mask)


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings without a data-dependent early exit.

    Returns False early if lengths differ (this leaks the length, which
    is acceptable since lengths are typically public). Otherwise, every
    byte is XOR-ed and OR-ed together, so all bytes are always compared
    regardless of when a mismatch occurs. As with everything in this
    module, that is the data-oblivious discipline, not a CPython timing
    guarantee (#311); ``hmac.compare_digest`` is the primitive a real
    deployment would use.

    Args:
        a: First byte string.
        b: Second byte string.

    Returns:
        True if the strings are identical.
    """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def fixed_iteration_map(
    items: list[T], fn: Callable[[T], Any], max_size: int, sentinel: T
) -> list[Any]:
    """Apply a function over exactly ``max_size`` iterations.

    If the list is shorter than ``max_size``, the remaining iterations
    use the ``sentinel`` value, so the iteration *count* is independent of
    the actual list size. The per-iteration work still runs under CPython,
    which makes no constant-cycle promise (#311).

    Args:
        items: The list to map over.
        fn: The function to apply.
        max_size: The fixed number of iterations (must be ≥ len(items)).
        sentinel: Placeholder value for out-of-range indices.

    Returns:
        A list of exactly ``max_size`` results.
    """
    results = []
    for i in range(max_size):
        item = items[i] if i < len(items) else sentinel
        results.append(fn(item))
    return results


def oblivious_access(data: list[T], index: int, default: T) -> T:
    """Data-oblivious array access: every element is always read.

    The access *pattern* is independent of ``index`` — the discipline that,
    in a compiled enclave, denies cache-based side channels the accessed
    location. Under CPython this specifies the shape without carrying the
    guarantee (#311).

    Args:
        data: The array to access.
        index: The desired index.
        default: Default value if index is out of range.

    Returns:
        ``data[index]`` if ``0 ≤ index < len(data)``, else ``default``.
    """
    result = default
    for i in range(len(data)):
        mask = 1 if i == index else 0
        result = cmov(mask == 1, data[i], result)
    return result
