import io
import json
import logging
import subprocess
import sys
import time

from src.nomos.committee.members import ExampleRewardMember, ExampleSafetyMember
from src.nomos.models import PriorityTag, Proposal
from src.nomos.observability import configure_logging
from src.nomos.speaker import SpeakerStateMachine


def _make_proposal(
    member_id: str,
    tag: int = PriorityTag.ROUTINE,
    risk: float = 0.0,
    reward: float = 0.5,
    coherence: float = 1.0,
) -> Proposal:
    return Proposal(
        member_id=member_id,
        action=f"action_{member_id}",
        tag=tag,
        timestamp=time.time(),
        metadata={
            "expected_reward": reward,
            "risk": risk,
            "identity_coherence": coherence,
        },
    )


def _parse_json_docs(text):
    """Parse consecutive JSON documents (compact lines or pretty multi-line)."""
    decoder = json.JSONDecoder()
    idx = 0
    docs = []
    while idx < len(text):
        while idx < len(text) and text[idx] in " \t\r\n":
            idx += 1
        if idx >= len(text):
            break
        doc, idx = decoder.raw_decode(text, idx)
        docs.append(doc)
    return docs


def _capture(fmt: str = "plain", level: str = "info"):
    """Configure logging redirected to a StringIO and return (logger, buf).

    ``configure_logging`` binds its own ``StreamHandler(sys.stderr)`` at
    construction time, so swapping ``sys.stderr`` before configuring makes the
    emitted lines land in ``buf`` — no handler copying, no shared-state leaks.
    """
    buf = io.StringIO()
    real_stderr = sys.stderr
    sys.stderr = buf
    try:
        configure_logging(fmt=fmt, level=level)
        logger = logging.getLogger("nomos")
        return logger, buf
    finally:
        sys.stderr = real_stderr


def _parse_json_lines(buf):
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


class TestConfigureLogging:
    def test_plain_default(self):
        logger, buf = _capture()
        logger.info("hello", extra={"event": "ping"})
        line = buf.getvalue().strip()
        assert line.startswith("INFO")
        assert "hello" in line
        assert "event" not in line

    def test_json_format(self):
        logger, buf = _capture(fmt="json")
        logger.info("hello", extra={"event": "ping", "n": 7})
        records = _parse_json_docs(buf.getvalue())
        assert len(records) == 1
        rec = records[0]
        assert rec["message"] == "hello"
        assert rec["event"] == "ping"
        assert rec["n"] == 7
        assert rec["level"] == "INFO"
        assert "timestamp" in rec
        assert "logger" in rec

    def test_json_pretty_format(self):
        logger, buf = _capture(fmt="json-pretty")
        logger.info("hi", extra={"event": "x"})
        assert "\n" in buf.getvalue().strip()
        records = _parse_json_docs(buf.getvalue())
        assert records[0]["message"] == "hi"

    def test_level_debug(self):
        logger, buf = _capture(fmt="json", level="debug")
        logger.debug("dbg", extra={"event": "d"})
        logger.info("inf", extra={"event": "i"})
        assert any(r["message"] == "dbg" for r in _parse_json_docs(buf.getvalue()))
        assert any(r["message"] == "inf" for r in _parse_json_docs(buf.getvalue()))

    def test_level_info_suppresses_debug(self):
        logger, buf = _capture(fmt="json", level="info")
        logger.debug("dbg", extra={"event": "d"})
        assert _parse_json_docs(buf.getvalue()) == []

    def test_plain_json_roundtrip_valid(self):
        logger, buf = _capture(fmt="json")
        for i in range(3):
            logger.info("msg", extra={"event": "tick", "i": i})
        records = _parse_json_docs(buf.getvalue())
        assert [r["i"] for r in records] == [0, 1, 2]


class TestSpeakerTelemetry:
    def _speaker(self):
        return SpeakerStateMachine(
            members={"reward": ExampleRewardMember(), "safety": ExampleSafetyMember()},
            default_action="shutdown",
        )

    def test_cycle_emits_decision_event(self):
        _, buf = _capture(fmt="json", level="info")
        speaker = self._speaker()
        proposal = _make_proposal("reward")
        speaker.run_governance_cycle(state="normal", raw_proposals=[proposal])
        records = _parse_json_docs(buf.getvalue())
        events = [r["event"] for r in records]
        assert "governance_cycle_start" in events
        assert "governance_decision" in events

    def test_decision_has_action_and_round(self):
        _, buf = _capture(fmt="json", level="info")
        speaker = self._speaker()
        proposal = _make_proposal("reward")
        decision = speaker.run_governance_cycle(state="normal", raw_proposals=[proposal])
        records = _parse_json_docs(buf.getvalue())
        decision_rec = [r for r in records if r["event"] == "governance_decision"][0]
        assert decision_rec["action"] == decision.action
        assert decision_rec["round"] == 1
        assert decision_rec["is_default"] is False
        assert "falsification_counts" in decision_rec

    def test_extra_context_included(self):
        _, buf = _capture(fmt="json", level="info")
        speaker = self._speaker()
        from src.nomos.models import PriorityTag

        proposal = _make_proposal("reward", tag=PriorityTag.ROUTINE)
        speaker.run_governance_cycle(
            state="normal",
            raw_proposals=[proposal],
            extra_context={"strategy": "pipeline_test", "run_id": "abc-123"},
        )
        records = _parse_json_docs(buf.getvalue())
        assert all(r.get("strategy") == "pipeline_test" for r in records)
        assert all(r.get("run_id") == "abc-123" for r in records)

    def test_extra_context_never_changes_decision(self):
        _, buf = _capture(fmt="json", level="info")
        speaker = self._speaker()
        proposal = _make_proposal("reward")
        d1 = speaker.run_governance_cycle(state="normal", raw_proposals=[proposal])
        d2 = speaker.run_governance_cycle(
            state="normal",
            raw_proposals=[proposal],
            extra_context={"strategy": "evil", "phase": "hack"},
        )
        assert d1.action == d2.action
        assert d1.scores == d2.scores


class TestRunnerCli:
    def test_cli_json_flag_produces_json_lines(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.nomos.runner", "--log-format", "json", "speaker"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json.loads(line)

    def test_cli_plain_flag_stays_human(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.nomos.runner", "speaker"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "likely won" in result.stdout or "Decision:" in result.stdout
