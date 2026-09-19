---
title: "API reference for the Nomos Python package"
description: "Reference for the Nomos Python package: Speaker, Parliament members, identity core, Ulysses contracts, TEE modules, experiments, and benchmark utilities."
---

# API Reference

::: nomos.speaker
::: nomos.models
::: nomos.committee.base
::: nomos.committee.members
::: nomos.identity.core
::: nomos.identity.tiers
::: nomos.identity.keys
::: nomos.contracts.contract
::: nomos.contracts.enforcement
::: nomos.contracts.merger
!!! warning "TEE modules: simulated — not a security boundary"
    The four `nomos.tee` modules below are an executable specification of
    Appendix A's interface, not a hardened TEE (#311): sealing is a
    plaintext in-process dict, the measurement is a SHA-256 of the enclave
    module's own source (or a caller-supplied code hash), attestation is
    unsigned and cannot fail, batch validation returns an unsigned tuple
    (nothing in the codebase produces a cryptographic signature — the
    genesis multisig's `sign` records a simulated quorum vote), the
    watchdog is a pure-Python timer, and the constant-time helpers specify
    a data-oblivious discipline CPython cannot actually guarantee. The tee
    code with consumers outside its own tests is the watchdog/deadlock
    breaker (constructed by the server, the runner, and the agent
    pipeline) and `merkle_root` (called by `nomos.audit`'s log chaining);
    `SimulatedEnclave`, `BatchVerifier` and `constant_time` are exercised
    only by their unit tests.

::: nomos.tee.enclave
::: nomos.tee.batch
::: nomos.tee.watchdog
::: nomos.tee.constant_time
::: nomos.server
::: nomos.experiments.base
::: nomos.benchmarks.baselines
::: nomos.benchmarks.analysis
