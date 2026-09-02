"""Hold the canonical negative-result phrasing identical everywhere (#278).

The transferable finding — asserted-metadata safety checks fall to
optimization pressure — is the project's citable claim, and #278 requires one
canonical phrasing reused verbatim across every public surface so citations
converge. A paraphrase that drifts on scope ("some proposals", "a large
model", "when told the mechanism") changes what is being claimed; this test
makes any drift a red build instead of a quiet fork.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL_CLAIM = (
    "A safety check that scores proposer-supplied metadata has zero "
    "adversarial value: a 64×64-MLP PPO policy, given 100,000 training steps "
    "and never told the mechanism, learned to silence it on 100% of its "
    "genuinely unsafe proposals, on every seed."
)

FIELD_MAPPING = (
    "Wherever an agent self-declares the risk of its own actions, this is "
    "the failure mode; at least one independently grounded verifier is "
    "load-bearing."
)

SURFACES = [
    "README.md",
    "docs/index.md",
    "book/appendix-e-rl-adversary.md",
    "paper/ai4good-2026-draft.md",
]


class TestCanonicalClaim:
    def test_the_claim_appears_verbatim_on_every_surface(self):
        for surface in SURFACES:
            text = (ROOT / surface).read_text(encoding="utf-8")
            assert CANONICAL_CLAIM in text, (
                f"{surface} does not carry the canonical negative-result "
                f"claim verbatim (#278); edit it back or change the claim "
                f"everywhere at once, this test included"
            )

    def test_the_field_mapping_appears_verbatim_on_every_surface(self):
        for surface in SURFACES:
            text = (ROOT / surface).read_text(encoding="utf-8")
            assert FIELD_MAPPING in text, (
                f"{surface} does not carry the field-mapping sentence verbatim (#278)"
            )

    def test_the_claim_states_its_scope(self):
        for fragment in (
            "64×64-MLP",
            "100,000 training steps",
            "never told the mechanism",
            "100% of its genuinely unsafe proposals",
            "on every seed",
        ):
            assert fragment in CANONICAL_CLAIM
