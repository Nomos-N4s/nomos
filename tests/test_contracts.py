from src.nomos.contracts.contract import (
    ContractRegistry,
    ContractState,
    UlyssesContract,
)
from src.nomos.contracts.enforcement import (
    DistributedMonitor,
    enforce_distributed_monitors,
    enforce_procedural_inertia,
    enforce_timelock,
    stacked_enforcement,
)
from src.nomos.contracts.merger import apply_restrictions, merge_masks
from src.nomos.models import GovernanceDecision


class TestContractLifecycle:
    def test_proposed_to_enacted(self):
        c = UlyssesContract(
            contract_id="test_1",
            restricted_indices={1, 2},
        )
        assert c.state == ContractState.PROPOSED
        c.enact()
        assert c.state == ContractState.ENACTED
        c.activate()
        assert c.state == ContractState.ACTIVE
        c.revoke()
        assert c.state == ContractState.REVOKED

    def test_only_active_applies(self):
        c = UlyssesContract(
            contract_id="test_2",
            restricted_indices={0},
        )
        assert not c.applies_to(0)
        c.enact()
        assert c.applies_to(0)
        c.revoke()
        assert not c.applies_to(0)

    def test_is_active_property(self):
        c = UlyssesContract(contract_id="t", restricted_indices=set())
        assert not c.is_active
        c.enact()
        assert c.is_active
        c.revoke()
        assert not c.is_active

    def test_applies_to_right_index(self):
        c = UlyssesContract(contract_id="t", restricted_indices={1, 3, 5})
        c.enact()
        assert c.applies_to(1)
        assert c.applies_to(3)
        assert not c.applies_to(0)
        assert not c.applies_to(2)

    def test_contract_repr(self):
        c = UlyssesContract(contract_id="c1", restricted_indices={0, 1})
        c.enact()
        r = repr(c)
        assert "c1" in r
        assert "ENACTED" in r

    def test_enactment_threshold_default(self):
        c = UlyssesContract(contract_id="t", restricted_indices=set())
        assert c.enactment_threshold == 0.66

    def test_revocation_threshold_default(self):
        c = UlyssesContract(contract_id="t", restricted_indices=set())
        assert c.revocation_threshold == 1.0

    def test_enforcement_mode_default(self):
        c = UlyssesContract(contract_id="t", restricted_indices=set())
        assert c.enforcement_mode == "procedural_inertia"


class TestContractRegistry:
    def test_add_and_get_active(self):
        reg = ContractRegistry()
        c = UlyssesContract(contract_id="c1", restricted_indices={0})
        reg.add(c)
        assert len(reg.get_active()) == 0
        c.enact()
        assert len(reg.get_active()) == 1

    def test_get_by_id(self):
        reg = ContractRegistry()
        c = UlyssesContract(contract_id="my_id", restricted_indices={1})
        reg.add(c)
        assert reg.get_by_id("my_id") is c
        assert reg.get_by_id("nonexistent") is None

    def test_active_restrictions(self):
        reg = ContractRegistry()
        c1 = UlyssesContract(contract_id="c1", restricted_indices={0, 1})
        c2 = UlyssesContract(contract_id="c2", restricted_indices={2, 3})
        c1.enact()
        c2.enact()
        reg.add(c1)
        reg.add(c2)
        restrictions = reg.active_restrictions()
        assert restrictions == {0, 1, 2, 3}

    def test_tick_cycle(self):
        reg = ContractRegistry()
        assert reg._cycle == 0
        reg.tick_cycle()
        assert reg._cycle == 1

    def test_revoked_not_active(self):
        reg = ContractRegistry()
        c = UlyssesContract(contract_id="c1", restricted_indices={0})
        c.enact()
        reg.add(c)
        assert len(reg.get_active()) == 1
        c.revoke()
        assert len(reg.get_active()) == 0


class TestEnforcement:
    def test_procedural_inertia_maintains_by_default(self):
        contract = UlyssesContract(contract_id="t", restricted_indices={0})
        result = enforce_procedural_inertia(contract, 0.5)
        assert result.compliant is True

    def test_procedural_inertia_revoked_at_threshold(self):
        contract = UlyssesContract(
            contract_id="t", restricted_indices={0}, revocation_threshold=0.8,
        )
        result = enforce_procedural_inertia(contract, 0.9)
        assert result.compliant is False

    def test_distributed_monitor_passes(self):
        monitor = DistributedMonitor(
            monitor_id="m1",
            evaluate_fn=lambda idx, ctx: True,
        )
        result = enforce_distributed_monitors([monitor], 0, None)
        assert result.compliant is True

    def test_distributed_monitor_fails(self):
        monitor = DistributedMonitor(
            monitor_id="m1",
            evaluate_fn=lambda idx, ctx: False,
        )
        result = enforce_distributed_monitors([monitor], 0, None)
        assert result.compliant is False

    def test_timelock_no_lock(self):
        contract = UlyssesContract(contract_id="t", restricted_indices={0})
        result = enforce_timelock(contract, 0)
        assert result.compliant is True

    def test_timelock_active(self):
        contract = UlyssesContract(
            contract_id="t", restricted_indices={0}, timelock_blocks=100,
        )
        result = enforce_timelock(contract, 50)
        assert result.compliant is True

    def test_timelock_expired(self):
        contract = UlyssesContract(
            contract_id="t", restricted_indices={0}, timelock_blocks=100,
        )
        result = enforce_timelock(contract, 150)
        assert result.compliant is False

    def test_stacked_enforcement_all_pass(self):
        contract = UlyssesContract(contract_id="t", restricted_indices={0})
        monitor = DistributedMonitor("m1", lambda i, ctx: True)
        result = stacked_enforcement(contract, 0.5, [monitor], 0, None, 0)
        assert result.compliant is True

    def test_stacked_enforcement_first_fail_shortcircuits(self):
        contract = UlyssesContract(
            contract_id="t", restricted_indices={0}, revocation_threshold=0.0,
        )
        monitor = DistributedMonitor("m1", lambda i, ctx: True)
        result = stacked_enforcement(contract, 0.5, [monitor], 0, None, 0)
        assert result.compliant is False
        assert "Revocation threshold" in result.reason


class TestMaskMerger:
    def test_apply_restrictions(self):
        allowed = {0, 1, 2, 3}
        restricted = {1, 3}
        result = apply_restrictions(allowed, restricted)
        assert result == {0, 2}

    def test_no_overlap(self):
        allowed = {0, 1}
        restricted = {2, 3}
        result = apply_restrictions(allowed, restricted)
        assert result == {0, 1}

    def test_all_restricted(self):
        allowed = {0, 1}
        restricted = {0, 1}
        result = apply_restrictions(allowed, restricted)
        assert result == set()

    def test_merge_masks_adds_meta(self):
        decision = GovernanceDecision(
            action="test",
            governance_meta={"action_mask": [0, 1, 2, 3]},
        )
        reg = ContractRegistry()
        c = UlyssesContract(contract_id="c1", restricted_indices={2})
        c.enact()
        reg.add(c)
        merged = merge_masks(decision, reg)
        assert merged.governance_meta["contract_restrictions_applied"] == 1
        assert merged.governance_meta["final_action_count"] == 3

    def test_extract_mask_empty(self):
        from src.nomos.contracts.merger import _extract_mask
        decision = GovernanceDecision(action="test")
        mask = _extract_mask(decision)
        assert mask == set()
