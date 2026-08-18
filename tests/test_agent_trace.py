"""Tests for the governance trace writer, viewer data, and HTML export (#142)."""

import pytest

from src.nomos.agents import GovernorComparisonHarness, StubBackend
from src.nomos.agents.scenarios import TemptationBankLLM
from src.nomos.agents.trace import (
    TRACE_KEYS,
    build_run_viewer_html,
    build_viewer_data,
    build_viewer_data_from_events,
    load_trace_jsonl,
    write_run_viewer_html,
    write_trace_jsonl,
)
from src.nomos.committee.members import ExampleRewardMember, ExampleSafetyMember
from src.nomos.speaker import SpeakerStateMachine


def _run_pair(script=(0, 2, 1, 1)):
    """Harness pair on TemptationBank: loan, propose contract, work, work."""
    harness = GovernorComparisonHarness(
        lambda speaker: TemptationBankLLM(speaker),
        StubBackend(script=list(script)),
        TemptationBankLLM.action_space(),
        SpeakerStateMachine(
            members={"reward": ExampleRewardMember(), "safety": ExampleSafetyMember()},
            default_action="work",
        ),
        observation_fn=lambda s: s.render_observation(),
    )
    return harness.run_pair(seed=0, steps=len(script))


def _events_by_step(events, step: int, arm: str):
    return [e for e in events if e["step"] == step and e["arm"] == arm][0]


# ----------------------------------------------------------------------
# JSONL event log
# ----------------------------------------------------------------------


class TestTraceWriter:
    def test_jsonl_schema_and_ordering(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_trace_jsonl([pair], "temptation", output_dir=str(tmp_path))
        events = load_trace_jsonl(path)
        assert len(events) == 8  # 4 steps x 2 arms
        assert sorted(events[0]) == sorted(TRACE_KEYS)
        for event in events:
            assert sorted(event) == sorted(TRACE_KEYS)
        assert (events[0]["step"], events[0]["arm"]) == (0, "governed")
        assert (events[1]["step"], events[1]["arm"]) == (0, "ungoverned")
        assert (events[2]["step"], events[2]["arm"]) == (1, "governed")

    def test_veto_event_records_scores_and_reason(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_trace_jsonl([pair], "temptation", output_dir=str(tmp_path))
        events = load_trace_jsonl(path)
        loan_step = _events_by_step(events, 0, "governed")
        assert loan_step["decision"]["vetoed"] is True
        assert loan_step["decision"]["is_default"] is True
        assert loan_step["veto_reason"] == "vetoed by safety"
        assert loan_step["committee_scores"]["safety"] == pytest.approx(0.3)
        assert loan_step["committee_scores"]["reward"] == pytest.approx(0.9)
        assert loan_step["latency_ms"] >= 0.0

    def test_contract_state_recorded_after_enactment(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_trace_jsonl([pair], "temptation", output_dir=str(tmp_path))
        events = load_trace_jsonl(path)
        contract_step = _events_by_step(events, 1, "governed")
        assert contract_step["contract_state"] == [
            {
                "contract_id": "ban_loans",
                "state": "ACTIVE",
                "restricted_indices": [0],
                "timelock_blocks": 0,
            }
        ]


# ----------------------------------------------------------------------
# Viewer data structures
# ----------------------------------------------------------------------


class TestViewerData:
    def test_structure_complete_and_ordered(self) -> None:
        pair = _run_pair()
        viewer = build_viewer_data([pair], "run1")
        assert viewer["run_id"] == "run1"
        assert viewer["schema_version"] == 1
        assert viewer["num_steps"] == 4
        assert viewer["members"] == ["reward", "safety"]
        assert viewer["contract_ids"] == ["ban_loans"]
        assert [s["step"] for s in viewer["steps"]] == [0, 1, 2, 3]
        for step in viewer["steps"]:
            assert step["governed"] is not None
            assert step["ungoverned"] is not None
            assert sorted(step["governed"]) == sorted(TRACE_KEYS)

    def test_events_roundtrip_matches_pairs(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_trace_jsonl([pair], "run1", output_dir=str(tmp_path))
        from_events = build_viewer_data_from_events(load_trace_jsonl(path), "run1")
        assert from_events == build_viewer_data([pair], "run1")


# ----------------------------------------------------------------------
# Self-contained HTML export
# ----------------------------------------------------------------------


class TestHtmlExport:
    @staticmethod
    def _read(path: str) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_export_nonempty_with_sections(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_run_viewer_html([pair], "run1", output_dir=str(tmp_path))
        html = self._read(path)
        assert len(html) > 2000
        for section in (
            "Governance Trace",
            "Timeline",
            "Veto heatmap",
            "Contract lifecycle",
            "Side-by-side replay",
            "ban_loans",
        ):
            assert section in html

    def test_export_embeds_serialised_run(self, tmp_path) -> None:
        pair = _run_pair()
        path = write_run_viewer_html([pair], "run1", output_dir=str(tmp_path))
        html = self._read(path)
        assert '"run_id": "run1"' in html
        assert '"num_steps": 4' in html

    def test_build_html_accepts_title_override(self) -> None:
        pair = _run_pair()
        viewer = build_viewer_data([pair], "run1")
        html = build_run_viewer_html(viewer, title="Review Copy")
        assert "<title>Review Copy</title>" in html
