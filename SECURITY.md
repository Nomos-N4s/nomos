# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |

This is a **pre-alpha research prototype**. The security model is aspirational and
under active development. See [`book/appendix-a/tee-isolation.md`](book/appendix-a/tee-isolation.md)
for the full TEE threat model.

## Security Model

Nomos relies on Trusted Execution Environments (TEEs) for
runtime isolation of Parliament members. The architecture is described in
Appendix A and covers:

- **Hardware trust anchors**: Intel SGX, AMD SEV-SNP, Arm TrustZone
- **Single-enclave architecture** with multi-enclave consensus addendum
- **Hardware watchdog** for deadlock detection and cold-boot recovery (§A.9.5)
- **Constant-time execution** to mitigate timing side channels (§A.8)
- **Merkle-tree batch verification** for integrity proofs (§A.6)

### Known Residual Risks

These are fundamental physical-world limits, acknowledged by the review panel:

1. **Social engineering** — no TEE can prevent authorized users from being coerced
2. **Hardware supply chain** — malicious silicon cannot be detected post-fabrication
3. **Adaptive proxy gap** — a user could voluntarily proxy decisions to an
   ungoverned system outside the TEE

See [`book/responses/response-to-review-panel.md`](book/responses/response-to-review-panel.md)
for the full discussion.

## Reporting a Vulnerability

If you discover a vulnerability in the reference implementation, please open a
[GitHub Issue](https://github.com/xcoder-es/nomos/issues)
with the label `security`. Do not disclose the vulnerability publicly until it
has been addressed.

For vulnerabilities in the theoretical framework, please open a standard issue
with the label `theory`.

We aim to acknowledge reports within 48 hours and provide a fix timeline within
7 business days.

## Dependencies

Dependencies are pinned in `pyproject.toml`. Run `uv sync` to install from the
lock file. See [`book/appendix-c/data-types.md`](book/appendix-c/data-types.md)
for the dependency reference.
