import hashlib
import time

from src.governance.identity.keys import GenesisManifest
from src.governance.tee.batch import (
    BatchProposal,
    BatchVerifier,
    compute_diversity,
    merkle_root,
)
from src.governance.tee.constant_time import (
    cmov,
    constant_time_compare,
    fixed_iteration_map,
    oblivious_access,
)
from src.governance.tee.enclave import AttestationReport, SimulatedEnclave
from src.governance.tee.watchdog import (
    DeadlockBreaker,
    WatchdogState,
    WatchdogTimer,
)


class TestSimulatedEnclave:
    def test_attest_returns_valid_report(self):
        enclave = SimulatedEnclave()
        report = enclave.attest()
        assert isinstance(report, AttestationReport)
        assert report.valid is True
        assert report.is_debug is False
        assert len(report.enclave_hash) == 64

    def test_is_attested_after_attest(self):
        enclave = SimulatedEnclave()
        assert enclave.is_attested is False
        enclave.attest()
        assert enclave.is_attested is True

    def test_seal_and_unseal(self):
        enclave = SimulatedEnclave()
        enclave.seal("key1", "value1")
        enclave.seal("key2", 42)
        assert enclave.unseal("key1") == "value1"
        assert enclave.unseal("key2") == 42

    def test_unseal_missing_key(self):
        enclave = SimulatedEnclave()
        assert enclave.unseal("nonexistent") is None

    def test_verify_measurement(self):
        enclave = SimulatedEnclave()
        report = enclave.attest()
        assert enclave.verify_measurement(report.enclave_hash) is True

    def test_verify_measurement_wrong_hash(self):
        enclave = SimulatedEnclave()
        assert enclave.verify_measurement("deadbeef") is False

    def test_cold_boot_resets_state(self):
        genesis = GenesisManifest()
        enclave = SimulatedEnclave(genesis=genesis)
        enclave.seal("persistent", "data")
        enclave.attest()
        old_hash = enclave._measurement

        enclave.cold_boot(genesis)

        assert enclave.unseal("persistent") is None
        assert enclave.is_attested is False
        assert enclave._measurement != old_hash


class TestMerkleRoot:
    def test_empty_list(self):
        result = merkle_root([])
        expected = hashlib.sha256(b"empty").hexdigest()
        assert result == expected

    def test_single_item(self):
        item = b"hello"
        result = merkle_root([item])
        expected = hashlib.sha256(item).hexdigest()
        assert result == expected

    def test_two_items(self):
        items = [b"a", b"b"]
        result = merkle_root(items)
        left = hashlib.sha256(b"a").hexdigest()
        right = hashlib.sha256(b"b").hexdigest()
        expected = hashlib.sha256((left + right).encode()).hexdigest()
        assert result == expected

    def test_deterministic(self):
        items = [b"x", b"y", b"z"]
        assert merkle_root(items) == merkle_root(items)

    def test_different_order_different_root(self):
        items_a = [b"a", b"b"]
        items_b = [b"b", b"a"]
        assert merkle_root(items_a) != merkle_root(items_b)

    def test_three_items(self):
        items = [b"1", b"2", b"3"]
        result = merkle_root(items)
        assert isinstance(result, str)
        assert len(result) == 64


class TestComputeDiversity:
    def test_all_unique(self):
        assert compute_diversity([1, 2, 3, 4]) == 1.0

    def test_all_same(self):
        assert compute_diversity([1, 1, 1]) == 1.0 / 3.0

    def test_empty_list(self):
        assert compute_diversity([]) == 1.0

    def test_single_element(self):
        assert compute_diversity([42]) == 1.0

    def test_some_duplicates(self):
        assert compute_diversity([1, 2, 2, 3, 3]) == 3.0 / 5.0


class TestBatchVerifier:
    def test_valid_batch_passes(self):
        verifier = BatchVerifier(risk_threshold=0.7, diversity_min=0.3)
        proposal = BatchProposal(
            action_indices=[1, 2, 3],
            aggregate_risk=0.3,
            diversity_score=0.8,
        )
        valid, message = verifier.validate_batch(proposal)
        assert valid is True
        assert "valid" in message.lower()

    def test_high_risk_rejected(self):
        verifier = BatchVerifier(risk_threshold=0.7, diversity_min=0.3)
        proposal = BatchProposal(
            action_indices=[1],
            aggregate_risk=0.9,
            diversity_score=1.0,
        )
        valid, message = verifier.validate_batch(proposal)
        assert valid is False
        assert "risk" in message.lower()

    def test_low_diversity_rejected(self):
        verifier = BatchVerifier(risk_threshold=0.7, diversity_min=0.5)
        proposal = BatchProposal(
            action_indices=[1, 1, 1],
            aggregate_risk=0.3,
            diversity_score=0.0,
        )
        valid, message = verifier.validate_batch(proposal)
        assert valid is False
        assert "diversity" in message.lower()

    def test_verify_valid_proof(self):
        verifier = BatchVerifier()

        leaf = hashlib.sha256(b"1").hexdigest()
        sibling1 = hashlib.sha256(b"2").hexdigest()
        left = hashlib.sha256((leaf + sibling1).encode()).hexdigest()
        sibling2 = hashlib.sha256(b"3").hexdigest()
        expected_root = hashlib.sha256((left + sibling2).encode()).hexdigest()

        proof = [sibling1, sibling2]
        assert verifier.verify_proof(1, proof, expected_root) is True

    def test_verify_invalid_proof(self):
        verifier = BatchVerifier()
        result = verifier.verify_proof(1, ["wrong"], "badroot")
        assert result is False


class TestWatchdogTimer:
    def test_initial_state_normal(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=100.0)
        assert watchdog.state == WatchdogState.NORMAL

    def test_heartbeat_updates_timestamp(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=100000.0)
        old_time = watchdog._last_heartbeat
        time.sleep(0.001)
        watchdog.heartbeat()
        assert watchdog._last_heartbeat > old_time

    def test_check_returns_normal_when_recent_heartbeat(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=100000.0)
        watchdog.heartbeat()
        assert watchdog.check() == WatchdogState.NORMAL

    def test_check_detects_missed_heartbeat(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        time.sleep(0.005)
        state = watchdog.check()
        assert state == WatchdogState.HEARTBEAT_MISSED

    def test_heartbeat_restores_from_missed(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        watchdog._state = WatchdogState.HEARTBEAT_MISSED
        watchdog.heartbeat()
        assert watchdog.state == WatchdogState.NORMAL

    def test_cold_boot_state_persists(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        watchdog._state = WatchdogState.COLD_BOOT
        assert watchdog.check() == WatchdogState.COLD_BOOT

    def test_get_events_returns_list(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        assert isinstance(watchdog.get_events(), list)

    def test_heartbeat_missed_logs_event(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        time.sleep(0.005)
        watchdog.check()
        events = watchdog.get_events()
        assert len(events) >= 1
        assert "heartbeat_missed" in events[0].event_type


class TestDeadlockBreaker:
    def test_initial_state(self):
        breaker = DeadlockBreaker(threshold_cycles=5)
        assert breaker.is_deadlocked is False
        assert breaker.stalled_cycles == 0
        assert breaker.total_cold_boots == 0

    def test_decision_produced_resets_counter(self):
        breaker = DeadlockBreaker(threshold_cycles=5)
        breaker.record_cycle(decision_produced=False)
        breaker.record_cycle(decision_produced=False)
        breaker.record_cycle(decision_produced=True)
        assert breaker.stalled_cycles == 0

    def test_threshold_triggers_cold_boot(self):
        breaker = DeadlockBreaker(threshold_cycles=3)
        for _ in range(3):
            breaker.record_cycle(decision_produced=False)
        assert breaker.check() is True
        assert breaker.total_cold_boots == 1

    def test_check_returns_false_after_cold_boot(self):
        breaker = DeadlockBreaker(threshold_cycles=3)
        for _ in range(3):
            breaker.record_cycle(decision_produced=False)
        breaker.check()
        assert breaker.check() is False

    def test_is_deadlocked_at_threshold(self):
        breaker = DeadlockBreaker(threshold_cycles=2)
        breaker.record_cycle(decision_produced=False)
        assert breaker.is_deadlocked is False
        breaker.record_cycle(decision_produced=False)
        assert breaker.is_deadlocked is True

    def test_reset_clears_state(self):
        breaker = DeadlockBreaker(threshold_cycles=2)
        for _ in range(3):
            breaker.record_cycle(decision_produced=False)
        breaker.check()
        breaker.reset()
        assert breaker.stalled_cycles == 0
        assert breaker.is_deadlocked is False
        assert breaker.total_cold_boots == 1

    def test_no_trigger_below_threshold(self):
        breaker = DeadlockBreaker(threshold_cycles=5)
        for _ in range(4):
            breaker.record_cycle(decision_produced=False)
        assert breaker.check() is False
        assert breaker.total_cold_boots == 0


class TestConstantTime:
    def test_cmov_selects_a_when_true(self):
        assert cmov(True, 10, 20) == 10

    def test_cmov_selects_b_when_false(self):
        assert cmov(False, 10, 20) == 20

    def test_cmov_with_strings(self):
        assert cmov(True, "a", "b") == "a"
        assert cmov(False, "a", "b") == "b"

    def test_cmov_with_floats(self):
        assert cmov(True, 1.5, 2.5) == 1.5
        assert cmov(False, 1.5, 2.5) == 2.5

    def test_constant_time_compare_equal(self):
        assert constant_time_compare(b"hello", b"hello") is True

    def test_constant_time_compare_different(self):
        assert constant_time_compare(b"hello", b"world") is False

    def test_constant_time_compare_different_length(self):
        assert constant_time_compare(b"abc", b"abcd") is False

    def test_constant_time_compare_empty(self):
        assert constant_time_compare(b"", b"") is True

    def test_fixed_iteration_map_respects_max_size(self):
        result = fixed_iteration_map([1, 2, 3], lambda x: x * 2,
                                      max_size=5, sentinel=0)
        assert result == [2, 4, 6, 0, 0]

    def test_fixed_iteration_map_exact_size(self):
        result = fixed_iteration_map([1, 2], lambda x: x + 1,
                                      max_size=2, sentinel=-1)
        assert result == [2, 3]

    def test_oblivious_access_finds_item(self):
        data = [10, 20, 30, 40]
        assert oblivious_access(data, 2, default=-1) == 30

    def test_oblivious_access_out_of_bounds(self):
        data = [10, 20]
        assert oblivious_access(data, 5, default=-1) == -1

    def test_oblivious_access_empty_list(self):
        assert oblivious_access([], 0, default=42) == 42
