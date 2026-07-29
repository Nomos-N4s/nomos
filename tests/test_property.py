import hashlib

from hypothesis import assume, given
from hypothesis import strategies as st

from src.governance.committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExampleMemoryMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
    ExampleSocialMember,
)
from src.governance.models import PriorityTag, Proposal
from src.governance.speaker import SpeakerStateMachine

from src.governance.contracts.contract import ContractState, UlyssesContract
from src.governance.contracts.enforcement import (
    enforce_procedural_inertia,
    enforce_timelock,
    stacked_enforcement,
)
from src.governance.contracts.merger import apply_restrictions
from src.governance.identity.keys import GenesisMultisig
from src.governance.identity.ontology import compute_hash
from src.governance.identity.tiers import TIER_RULES, MutabilityTier
from src.governance.tee.batch import merkle_root
from src.governance.tee.constant_time import cmov, constant_time_compare, oblivious_access
from src.governance.tee.watchdog import DeadlockBreaker, WatchdogState, WatchdogTimer

ALL_MEMBERS = {
    "reward": ExampleRewardMember(),
    "safety": ExampleSafetyMember(),
    "integrity": ExampleIntegrityMember(),
    "curiosity": ExampleCuriosityMember(),
    "planning": ExamplePlanningMember(),
    "social": ExampleSocialMember(),
    "memory": ExampleMemoryMember(),
}

MEMBER_IDS = list(ALL_MEMBERS.keys())

TAGS = st.sampled_from([
    PriorityTag.CRITICAL_SAFETY,
    PriorityTag.HIGH_IMPACT,
    PriorityTag.ROUTINE,
    PriorityTag.EXPLORATORY,
    PriorityTag.INFORMATIONAL,
])

META = st.fixed_dictionaries({
    "expected_reward": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "risk": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "identity_coherence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "long_term_value": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "novelty": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "social_acceptability": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    "historical_consistency": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
})

PROPOSAL_STRATEGY = st.builds(
    Proposal,
    member_id=st.sampled_from(MEMBER_IDS),
    action=st.just("test_action"),
    tag=TAGS,
    timestamp=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
    metadata=META,
)

ACTION_INDEX = st.integers(min_value=0, max_value=100)
ACTION_SET = st.sets(ACTION_INDEX, min_size=0, max_size=20)
VOTE_FRACTION = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
THRESHOLD = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
BYTE_PAIR = st.tuples(st.binary(min_size=0, max_size=50), st.binary(min_size=0, max_size=50))


class TestPropertyBudgetInvariant:
    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=50))
    def test_budget_never_exceeded(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        total_budget = sum(m.budget for m in ALL_MEMBERS.values())
        assert len(agenda) <= total_budget

    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=50))
    def test_no_member_exceeds_individual_budget(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        counts = {}
        for p in agenda:
            counts[p.member_id] = counts.get(p.member_id, 0) + 1

        for member_id, member in ALL_MEMBERS.items():
            assert counts.get(member_id, 0) <= member.budget

    def test_unknown_members_skipped(self):
        speaker = SpeakerStateMachine(members={"reward": ExampleRewardMember()}, default_action="noop")
        proposals = [
            Proposal(member_id="unknown", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"risk": 0.0}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) == 0

    def test_budget_zero_excludes_all(self):
        member = ExampleRewardMember()
        member.budget = 0
        speaker = SpeakerStateMachine(members={"reward": member}, default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=float(i), metadata={"risk": 0.0})
            for i in range(5)
        ]
        agenda = speaker.set_agenda(proposals)
        assert len(agenda) == 0


class TestPropertyPriorityOrder:
    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=30))
    def test_agenda_sorted_by_tag_then_timestamp(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        agenda = speaker.set_agenda(proposals)

        for i in range(1, len(agenda)):
            prev = agenda[i - 1]
            curr = agenda[i]
            key_prev = (prev.tag, prev.timestamp)
            key_curr = (curr.tag, curr.timestamp)
            assert key_prev <= key_curr, (
                f"Agenda not sorted at index {i}: "
                f"({prev.tag}, {prev.timestamp}) > ({curr.tag}, {curr.timestamp})"
            )

    def test_critical_safety_first(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="r", tag=PriorityTag.ROUTINE,
                     timestamp=1.0, metadata={}),
            Proposal(member_id="safety", action="s", tag=PriorityTag.CRITICAL_SAFETY,
                     timestamp=2.0, metadata={}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert agenda[0].tag == PriorityTag.CRITICAL_SAFETY

    def test_informational_last(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        proposals = [
            Proposal(member_id="reward", action="r", tag=PriorityTag.INFORMATIONAL,
                     timestamp=1.0, metadata={}),
            Proposal(member_id="safety", action="s", tag=PriorityTag.ROUTINE,
                     timestamp=2.0, metadata={}),
        ]
        agenda = speaker.set_agenda(proposals)
        assert agenda[-1].tag == PriorityTag.INFORMATIONAL


class TestPropertyDefaultFallback:
    def test_empty_proposals_returns_default(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="emergency_shutdown")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.is_default is True
        assert decision.action == "emergency_shutdown"

    def test_empty_proposals_all_members(self):
        speaker = SpeakerStateMachine(members={"reward": ExampleRewardMember()}, default_action="fallback")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.is_default is True

    @given(proposals=st.lists(PROPOSAL_STRATEGY, min_size=0, max_size=20))
    def test_default_has_no_action_if_default_is_none(self, proposals):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action=None)
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=proposals)
        if decision.is_default:
            assert decision.action is None


class TestPropertyVetoBehavior:
    @given(risk=st.floats(min_value=0.9, max_value=1.0, allow_nan=False, allow_infinity=False))
    def test_high_risk_triggers_safety_veto(self, risk):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(members={"safety": safety}, default_action="shutdown")
        p = Proposal(member_id="safety", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.5, "risk": risk,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.is_default is True

    @given(risk=st.floats(min_value=0.0, max_value=0.3, allow_nan=False, allow_infinity=False))
    def test_low_risk_passes_safety_veto(self, risk):
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(members={"safety": safety}, default_action="shutdown")
        p = Proposal(member_id="safety", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.5, "risk": risk,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        if not decision.is_default:
            assert decision.action == "x"


class TestPropertyFalsification:
    def test_clean_proposals_no_falsification(self):
        integrity = ExampleIntegrityMember()
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"identity_coherence": 1.0, "risk": 0.0,
                                               "expected_reward": 0.5}),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta.get("falsification_counts", {})
        assert all(v == 0 for v in counts.values())

    def test_low_coherence_triggers_falsification(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"identity_coherence": 0.0, "risk": 0.0,
                                               "expected_reward": 0.5}),
        ]
        decision = speaker.run_governance_cycle("normal", proposals)
        counts = decision.governance_meta.get("falsification_counts", {})
        assert counts.get("reward", 0) >= 1

    def test_budget_halved_after_three_offenses(self):
        integrity = ExampleIntegrityMember()
        integrity.veto_threshold = 0.0
        reward = ExampleRewardMember()
        initial_budget = reward.budget
        speaker = SpeakerStateMachine(
            members={"reward": reward, "integrity": integrity},
            default_action="shutdown",
        )
        proposals = [
            Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=float(i), metadata={"identity_coherence": 0.0, "risk": 0.0,
                                                   "expected_reward": 0.5})
            for i in range(5)
        ]
        speaker.run_governance_cycle("normal", proposals)
        assert reward.budget <= initial_budget // 2


class TestPropertyVoting:
    def test_majority_passes_routine(self):
        reward = ExampleRewardMember()
        safety = ExampleSafetyMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward, "safety": safety},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="good_action", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 1.0, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert not decision.is_default
        assert decision.action == "good_action"

    def test_high_impact_requires_supermajority(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="risky", tag=PriorityTag.HIGH_IMPACT,
                     timestamp=0.0, metadata={"expected_reward": 0.4, "risk": 1.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="high_impact")
        assert decision.is_default is True

    def test_identity_class_requires_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="identity_change", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 0.8, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="identity")
        assert decision.is_default is True

    def test_identity_class_passes_at_unanimity(self):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
        )
        p = Proposal(member_id="reward", action="identity_change", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": 1.0, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p], decision_class="identity")
        assert not decision.is_default

    @given(st.floats(min_value=0.0, max_value=0.3, allow_nan=False, allow_infinity=False))
    def test_low_expected_reward_fails_single_member(self, low_reward):
        reward = ExampleRewardMember()
        speaker = SpeakerStateMachine(
            members={"reward": reward},
            default_action="shutdown",
            majority_threshold=0.5,
        )
        p = Proposal(member_id="reward", action="bad", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata={"expected_reward": low_reward, "risk": 0.0,
                                               "identity_coherence": 1.0})
        decision = speaker.run_governance_cycle("normal", [p])
        assert decision.is_default is True


class TestPropertyAllMembersParticipate:
    def test_all_seven_members_present_on_consensus(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        meta = {
            "expected_reward": 0.8, "risk": 0.0, "identity_coherence": 1.0,
            "long_term_value": 0.9, "novelty": 0.7, "social_acceptability": 0.9,
            "historical_consistency": 1.0,
        }
        p = Proposal(member_id="reward", action="x", tag=PriorityTag.ROUTINE,
                     timestamp=0.0, metadata=meta)
        decision = speaker.run_governance_cycle("normal", [p])
        assert len(decision.scores) == 7

    def test_default_decision_has_empty_scores(self):
        speaker = SpeakerStateMachine(members=dict(ALL_MEMBERS), default_action="noop")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[])
        assert decision.scores == {}


class TestPropertyMaskMerger:
    @given(allowed=ACTION_SET, restricted=ACTION_SET)
    def test_restrictions_never_add_actions(self, allowed, restricted):
        result = apply_restrictions(allowed, restricted)
        assert result <= allowed

    @given(allowed=ACTION_SET, restricted=ACTION_SET)
    def test_sequential_equals_union(self, allowed, restricted):
        r1 = {i for i in restricted if i % 2 == 0}
        r2 = {i for i in restricted if i % 2 == 1}
        sequential = apply_restrictions(apply_restrictions(allowed, r1), r2)
        union = apply_restrictions(allowed, r1 | r2)
        assert sequential == union

    @given(allowed=ACTION_SET)
    def test_empty_restriction_is_identity(self, allowed):
        assert apply_restrictions(allowed, set()) == allowed


class TestPropertyEnforcementMonotonicity:
    @given(vote=VOTE_FRACTION, threshold=THRESHOLD)
    def test_inertia_matches_threshold_logic(self, vote, threshold):
        contract = UlyssesContract(
            contract_id="test", restricted_indices={1}, revocation_threshold=threshold,
        )
        result = enforce_procedural_inertia(contract, vote)
        assert result.compliant == (vote < threshold)

    @given(vote=VOTE_FRACTION, t1=THRESHOLD, t2=THRESHOLD)
    def test_monotonic_in_revocation_threshold(self, vote, t1, t2):
        c1 = UlyssesContract(contract_id="a", restricted_indices={1}, revocation_threshold=t1)
        c2 = UlyssesContract(contract_id="b", restricted_indices={1}, revocation_threshold=t2)
        r1 = enforce_procedural_inertia(c1, vote)
        r2 = enforce_procedural_inertia(c2, vote)
        if t1 <= t2 and r1.compliant:
            assert r2.compliant

    @given(vote=VOTE_FRACTION, threshold=THRESHOLD)
    def test_stacked_short_circuits_on_inertia_failure(self, vote, threshold):
        contract = UlyssesContract(
            contract_id="test", restricted_indices={1}, revocation_threshold=threshold,
        )
        inertia = enforce_procedural_inertia(contract, vote)
        stacked = stacked_enforcement(contract, vote, [], 0, None, 0)
        if not inertia.compliant:
            assert not stacked.compliant
            assert stacked.reason == inertia.reason


class TestPropertyTimelockDecrement:
    @given(start_blocks=st.integers(min_value=0, max_value=100), ticks=st.integers(min_value=0, max_value=100))
    def test_timelock_expires_exactly_at_target_block(self, start_blocks, ticks):
        assume(start_blocks > 0)
        contract = UlyssesContract(
            contract_id="time_test", restricted_indices={1},
            timelock_blocks=start_blocks,
        )
        result = enforce_timelock(contract, ticks)
        assert result.compliant == (ticks < start_blocks)

    @given(blocks=st.integers(min_value=1, max_value=50))
    def test_timelock_remaining_decreases_with_ticks(self, blocks):
        contract = UlyssesContract(
            contract_id="time_test", restricted_indices={1},
            timelock_blocks=blocks, state=ContractState.ACTIVE,
        )
        from src.governance.contracts.contract import ContractRegistry
        reg = ContractRegistry()
        reg.add(contract)
        for cycle in range(blocks + 2):
            remaining = blocks - cycle
            result = enforce_timelock(contract, cycle)
            if remaining > 0:
                assert result.compliant
                assert "remaining" in result.reason
            else:
                assert not result.compliant
                assert "expired" in result.reason
            reg.tick_cycle()


class TestPropertyTierRules:
    def test_constitutional_requires_multisig(self):
        rule = TIER_RULES[MutabilityTier.CONSTITUTIONAL]
        assert rule.requires_external_multisig
        assert rule.requires_parliament_unanimity

    def test_operational_does_not_require_multisig(self):
        rule = TIER_RULES[MutabilityTier.OPERATIONAL]
        assert not rule.requires_external_multisig

    def test_immutable_cannot_modify(self):
        rule = TIER_RULES[MutabilityTier.IMMUTABLE]
        assert not rule.can_modify(MutabilityTier.IMMUTABLE)

    @given(tier=st.sampled_from([MutabilityTier.CONSTITUTIONAL, MutabilityTier.OPERATIONAL, MutabilityTier.DYNAMIC]))
    def test_non_immutable_tiers_can_modify(self, tier):
        rule = TIER_RULES[tier]
        assert rule.can_modify(tier)

    def test_all_tiers_have_positive_cooling_off(self):
        for tier, rule in TIER_RULES.items():
            assert rule.cooling_off_days >= 0

    def test_no_tier_accepts_negative_cooling_off(self):
        for rule in TIER_RULES.values():
            assert rule.cooling_off_days >= 0


class TestPropertyMultisigThresholds:
    @given(
        n_holders=st.integers(min_value=1, max_value=8),
        threshold=st.integers(min_value=1, max_value=8),
        sigs=st.integers(min_value=0, max_value=8),
    )
    def test_authorized_if_and_only_if_sigs_meet_threshold(self, n_holders, threshold, sigs):
        assume(threshold <= n_holders)
        msig = GenesisMultisig(threshold=threshold, total_holders=n_holders)
        for i in range(n_holders):
            msig.add_holder(f"holder_{i}")
        for i in range(min(sigs, n_holders)):
            msig.sign(f"holder_{i}")
        assert msig.is_authorized == (sigs >= threshold)

    @given(
        n_holders=st.integers(min_value=1, max_value=8),
    )
    def test_sign_idempotent(self, n_holders):
        msig = GenesisMultisig(threshold=n_holders, total_holders=n_holders)
        for i in range(n_holders):
            msig.add_holder(f"holder_{i}")
        msig.sign("holder_0")
        count_after_first = msig.signatures_count
        msig.sign("holder_0")
        assert msig.signatures_count == count_after_first


class TestPropertyOntologyHashDeterminism:
    @given(data=st.binary(min_size=0, max_size=200))
    def test_deterministic(self, data):
        assert compute_hash(data) == compute_hash(data)

    @given(data=st.binary(min_size=1, max_size=100))
    def test_different_inputs_different_hashes(self, data):
        assume(data != b"")
        other = bytes(b ^ 0xFF for b in data)
        assume(data != other)
        assert compute_hash(data) != compute_hash(other)


class TestPropertyWatchdogTransitions:
    def test_initial_state_normal(self):
        wd = WatchdogTimer()
        assert wd.state == WatchdogState.NORMAL

    def test_heartbeat_keeps_normal(self):
        wd = WatchdogTimer()
        wd.heartbeat()
        assert wd.state == WatchdogState.NORMAL

    def test_check_returns_cold_boot_sticky(self):
        wd = WatchdogTimer()
        wd._state = WatchdogState.COLD_BOOT
        result = wd.check()
        assert result == WatchdogState.COLD_BOOT

    def test_heartbeat_does_not_exit_cold_boot(self):
        wd = WatchdogTimer()
        wd._state = WatchdogState.COLD_BOOT
        wd.heartbeat()
        assert wd.state == WatchdogState.COLD_BOOT

    def test_heartbeat_restores_from_missed(self):
        wd = WatchdogTimer()
        wd._state = WatchdogState.HEARTBEAT_MISSED
        wd.heartbeat()
        assert wd.state == WatchdogState.NORMAL


class TestPropertyDeadlockBreaker:
    @given(threshold=st.integers(min_value=1, max_value=20), cycles=st.integers(min_value=0, max_value=50))
    def test_fires_exactly_once_when_threshold_reached(self, threshold, cycles):
        db = DeadlockBreaker(threshold_cycles=threshold)
        triggered = False
        for _ in range(cycles):
            db.record_cycle(decision_produced=False)
            if db.check():
                assert not triggered
                triggered = True
        assert triggered == (cycles >= threshold)

    def test_decision_produced_resets_counter(self):
        db = DeadlockBreaker(threshold_cycles=5)
        for _ in range(3):
            db.record_cycle(decision_produced=False)
        db.record_cycle(decision_produced=True)
        assert db.stalled_cycles == 0

    def test_reset_clears_trigger(self):
        db = DeadlockBreaker(threshold_cycles=2)
        db.record_cycle(decision_produced=False)
        db.record_cycle(decision_produced=False)
        db.check()
        assert db.total_cold_boots == 1
        db.reset()
        assert not db.is_deadlocked


EMPTY_MERKLE_ROOT = hashlib.sha256(b"empty").hexdigest()


class TestPropertyMerkleConsistency:
    @given(items=st.lists(st.binary(min_size=1, max_size=20), min_size=0, max_size=8))
    def test_deterministic(self, items):
        assert merkle_root(items) == merkle_root(items)

    @given(items=st.lists(st.binary(min_size=1, max_size=20), min_size=1, max_size=8))
    def test_root_changes_when_content_changes(self, items):
        first = merkle_root(items)
        modified = items[:]
        modified[0] = modified[0] + b"x"
        first_modified = merkle_root(modified)
        assert first != first_modified or items == modified

    def test_empty_root_is_known_constant(self):
        assert merkle_root([]) == EMPTY_MERKLE_ROOT

    @given(item=st.binary(min_size=1, max_size=50))
    def test_single_item_root(self, item):
        expected = hashlib.sha256(item).hexdigest()
        assert merkle_root([item]) == expected


class TestPropertyConstantTime:
    @given(pair=BYTE_PAIR)
    def test_compare_match(self, pair):
        a, b = pair
        assert constant_time_compare(a, b) == (a == b)

    @given(a=st.integers(min_value=-1000, max_value=1000), b=st.integers(min_value=-1000, max_value=1000))
    def test_cmov_selection(self, a, b):
        assert cmov(True, a, b) == a
        assert cmov(False, a, b) == b

    @given(
        data=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=20),
        idx=st.integers(min_value=0, max_value=50),
    )
    def test_oblivious_access_correctness(self, data, idx):
        default = -1
        result = oblivious_access(data, idx, default)
        if 0 <= idx < len(data):
            assert result == data[idx]
        else:
            assert result == default
