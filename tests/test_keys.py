import pytest

from src.nomos.identity.keys import GenesisManifest, GenesisMultisig, KeyHolder


class TestKeyHolder:
    def test_default_not_signed(self):
        kh = KeyHolder(name="alice", public_key="abc123")
        assert kh.has_signed is False

    def test_mark_signed(self):
        kh = KeyHolder(name="alice", public_key="abc123", has_signed=True)
        assert kh.has_signed is True


class TestGenesisMultisig:
    def test_default_threshold_3_of_5(self):
        ms = GenesisMultisig()
        assert ms.threshold == 3
        assert len(ms.holders) == 0

    def test_custom_threshold(self):
        ms = GenesisMultisig(threshold=2, total_holders=3)
        assert ms.threshold == 2

    def test_add_holder_generates_key(self):
        ms = GenesisMultisig()
        pk = ms.add_holder("alice")
        assert len(pk) == 16
        assert all(c in "0123456789abcdef" for c in pk)
        assert len(ms.holders) == 1
        assert ms.holders[0].name == "alice"

    def test_sign_valid_holder(self):
        ms = GenesisMultisig()
        ms.add_holder("alice")
        assert ms.sign("alice") is True
        assert ms.holders[0].has_signed is True

    def test_sign_unknown_holder(self):
        ms = GenesisMultisig()
        assert ms.sign("unknown") is False

    def test_sign_idempotent(self):
        ms = GenesisMultisig()
        ms.add_holder("alice")
        assert ms.sign("alice") is True
        assert ms.sign("alice") is False

    def test_signatures_count(self):
        ms = GenesisMultisig()
        ms.add_holder("alice")
        ms.add_holder("bob")
        assert ms.signatures_count == 0
        ms.sign("alice")
        assert ms.signatures_count == 1
        ms.sign("bob")
        assert ms.signatures_count == 2

    def test_is_authorized_below_threshold(self):
        ms = GenesisMultisig(threshold=3)
        for n in ["alice", "bob", "charlie"]:
            ms.add_holder(n)
        ms.sign("alice")
        ms.sign("bob")
        assert ms.is_authorized is False

    def test_is_authorized_at_threshold(self):
        ms = GenesisMultisig(threshold=3)
        for n in ["alice", "bob", "charlie"]:
            ms.add_holder(n)
        ms.sign("alice")
        ms.sign("bob")
        ms.sign("charlie")
        assert ms.is_authorized is True

    def test_reset_clears_signatures(self):
        ms = GenesisMultisig()
        ms.add_holder("alice")
        ms.sign("alice")
        assert ms.signatures_count == 1
        ms.reset()
        assert ms.signatures_count == 0
        assert ms.holders[0].has_signed is False


class TestGenesisQuorumIntegrity:
    """One principal must not be able to reach the quorum alone (issue #288),
    and the *n* in *t-of-n* must be enforced (issue #289).

    These mirror the Lean model in ``gov-budget-proof/GovBudgetProof/
    IdentityGenesis.lean``, where ``quorumCount`` filters a fixed key set so
    ``double_signing_cannot_reach_quorum_alone`` holds by construction.
    """

    def test_duplicate_name_is_rejected(self):
        ms = GenesisMultisig(threshold=3, total_holders=5)
        ms.add_holder("alice")
        with pytest.raises(ValueError, match="already registered"):
            ms.add_holder("alice")
        assert len(ms.holders) == 1

    def test_one_principal_cannot_reach_quorum_alone(self):
        ms = GenesisMultisig(threshold=3, total_holders=5)
        ms.add_holder("mallory")
        for _ in range(2):
            with pytest.raises(ValueError):
                ms.add_holder("mallory")
        for _ in range(3):
            ms.sign("mallory")
        assert ms.signatures_count == 1
        assert ms.is_authorized is False

    def test_signatures_count_is_distinct_by_name(self):
        ms = GenesisMultisig(threshold=3, total_holders=5)
        ms.add_holder("alice")
        # Defence in depth: even if a duplicate record is introduced by another
        # path, the quorum counts distinct names, as the Lean model does.
        ms.holders.append(KeyHolder(name="alice", public_key="deadbeef"))
        for h in ms.holders:
            h.has_signed = True
        assert ms.signatures_count == 1
        assert ms.is_authorized is False

    def test_cannot_register_more_than_total_holders(self):
        ms = GenesisMultisig(threshold=3, total_holders=5)
        for n in ["alice", "bob", "charlie", "diana", "eve"]:
            ms.add_holder(n)
        with pytest.raises(ValueError, match="total_holders=5"):
            ms.add_holder("frank")
        assert len(ms.holders) == 5

    def test_total_holders_is_stored(self):
        ms = GenesisMultisig(threshold=2, total_holders=3)
        assert ms.total_holders == 3

    def test_threshold_above_total_holders_is_rejected(self):
        with pytest.raises(ValueError, match="exceeds total_holders"):
            GenesisMultisig(threshold=9, total_holders=2)

    @pytest.mark.parametrize(
        "threshold,total_holders",
        [(0, 5), (3, 0), (-1, 5)],
    )
    def test_degenerate_configurations_are_rejected(self, threshold, total_holders):
        with pytest.raises(ValueError):
            GenesisMultisig(threshold=threshold, total_holders=total_holders)


class TestGenesisManifest:
    def test_defaults(self):
        m = GenesisManifest()
        assert m.is_sealed is False
        assert m.ontology_hash == ""

    def test_seal(self):
        m = GenesisManifest()
        assert m.is_sealed is False
        m.seal()
        assert m.is_sealed is True

    def test_has_multisig(self):
        m = GenesisManifest()
        assert isinstance(m.multisig, GenesisMultisig)
        assert m.multisig.threshold == 3

    def test_set_hashes(self):
        m = GenesisManifest()
        m.ontology_hash = "abc"
        m.core_commitments_hash = "def"
        m.parameter_envelope_hash = "ghi"
        m.member_set_hash = "jkl"
        assert m.ontology_hash == "abc"
        assert m.core_commitments_hash == "def"

    def test_repr(self):
        m = GenesisManifest()
        ms = m.multisig
        ms.add_holder("alice")
        ms.sign("alice")
        assert "sealed=False" in repr(m)
        assert "sigs=1/3" in repr(m)
        m.seal()
        assert "sealed=True" in repr(m)
