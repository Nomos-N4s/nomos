import pytest

from src.governance.identity.extension import (
    ExtensionCandidate,
    ExtensionPhase,
    ExtensionSandbox,
)
from src.governance.identity.keys import GenesisMultisig
from src.governance.identity.ontology import Ontology


class TestExtensionCandidate:
    def test_initial_phase_is_proposal(self):
        cand = ExtensionCandidate(index=1, operation="test", candidate_properties={"speed": 0.5})
        assert cand.phase == ExtensionPhase.PROPOSAL
        assert not cand.is_sandboxed

    def test_is_sandboxed_true_in_isolation_buffer(self):
        cand = ExtensionCandidate(index=1, operation="t", candidate_properties={})
        cand.phase = ExtensionPhase.ISOLATION_BUFFER
        assert cand.is_sandboxed


class TestExtensionSandbox:
    @pytest.fixture
    def setup(self):
        ontology = Ontology()
        multisig = GenesisMultisig(threshold=3, total_holders=5)
        for n in ["alice", "bob", "charlie", "diana", "eve"]:
            multisig.add_holder(n)
        sandbox = ExtensionSandbox(ontology, multisig)
        return ontology, multisig, sandbox

    def test_propose_new_index(self, setup):
        _, _, sandbox = setup
        cand = sandbox.propose(1, "jump", {"speed": 0.8, "risk": 0.2})
        assert cand.index == 1
        assert cand.operation == "jump"
        assert cand.phase == ExtensionPhase.PROPOSAL

    def test_propose_duplicate_index_raises(self, setup):
        ontology, _, sandbox = setup
        ontology.register(5, "existing", b"impl", {"a": 1.0})
        with pytest.raises(ValueError, match="already bound"):
            sandbox.propose(5, "dup", {"a": 1.0})

    def test_run_sandbox_populates_monitor_reports(self, setup):
        _, _, sandbox = setup
        sandbox.propose(2, "move", {"speed": 0.5, "safety": 0.5})
        sandbox.run_sandbox(2, rounds=3)
        cand = sandbox.get_candidate(2)
        assert len(cand.monitor_reports) == 3
        assert cand.phase == ExtensionPhase.ISOLATION_BUFFER

    def test_run_sandbox_nonexistent_candidate_does_nothing(self, setup):
        _, _, sandbox = setup
        sandbox.run_sandbox(99, rounds=3)
        assert sandbox.get_candidate(99) is None

    def test_audit_passes_within_tolerance(self, setup):
        _, _, sandbox = setup
        cand = sandbox.propose(3, "hop", {"speed": 0.5, "safety": 0.5})
        sandbox.run_sandbox(3, rounds=5)
        result = sandbox.audit(3, tolerance=0.3)
        assert result
        assert cand.phase != ExtensionPhase.REJECTED

    def test_audit_fails_beyond_tolerance(self, setup):
        _, _, sandbox = setup
        sandbox.propose(4, "leap", {"speed": 0.5, "safety": 0.5})
        cand = sandbox.get_candidate(4)
        cand.phase = ExtensionPhase.ISOLATION_BUFFER
        cand.empirical_properties = {"speed": 0.9, "safety": 0.1}
        assert not sandbox.audit(4, tolerance=0.1)
        assert sandbox.get_candidate(4).phase == ExtensionPhase.REJECTED

    def test_audit_nonexistent_returns_false(self, setup):
        _, _, sandbox = setup
        assert not sandbox.audit(99)

    def test_finalize_requires_multisig(self, setup):
        ontology, multisig, sandbox = setup
        sandbox.propose(10, "final_action", {"value": 0.5})
        sandbox.run_sandbox(10, rounds=3)
        assert not sandbox.finalize(10, b"impl_bytes")
        assert sandbox.get_candidate(10).phase == ExtensionPhase.REJECTED

    def test_finalize_success(self, setup):
        ontology, multisig, sandbox = setup
        sandbox.propose(11, "approved_action", {"value": 0.5})
        sandbox.run_sandbox(11, rounds=3)
        multisig.sign("alice")
        multisig.sign("bob")
        multisig.sign("charlie")
        assert multisig.is_authorized
        binding = sandbox.finalize(11, b"impl_bytes")
        assert binding is not None
        assert binding.index == 11
        assert sandbox.get_candidate(11).phase == ExtensionPhase.FINALIZED
        assert sandbox.get_candidate(11).runtime_hash == binding.runtime_hash
        assert ontology.has_index(11)

    def test_finalize_nonexistent_returns_none(self, setup):
        _, _, sandbox = setup
        assert sandbox.finalize(99, b"x") is None

    def test_finalize_rejected_if_audit_fails(self, setup):
        ontology, multisig, sandbox = setup
        cand = sandbox.propose(12, "deceptive", {"accuracy": 1.0})
        cand.phase = ExtensionPhase.ISOLATION_BUFFER
        cand.empirical_properties = {"accuracy": 0.0}
        multisig.sign("alice")
        multisig.sign("bob")
        multisig.sign("charlie")
        assert sandbox.finalize(12, b"impl") is None
        assert sandbox.get_candidate(12).phase == ExtensionPhase.REJECTED

    def test_get_candidate(self, setup):
        _, _, sandbox = setup
        sandbox.propose(7, "get_test", {"x": 1.0})
        c = sandbox.get_candidate(7)
        assert c is not None
        assert c.index == 7
        assert sandbox.get_candidate(999) is None
