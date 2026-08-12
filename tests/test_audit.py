"""Tests for the tamper-evident audit log (#164)."""

import json
import re

import pytest

from src.nomos.audit import ENTITY_TYPES, ZERO_HASH, AuditLog, AuditRecord, AuditVerification
from src.nomos.tee.batch import merkle_root


def _fixed_now(value: str = "2026-08-11T15:00:00.000Z"):
    """A fixed clock so identical runs produce identical logs."""
    return lambda: value


def _make_log(tmp_path, count: int = 5, payload=None):
    log = AuditLog(tmp_path / "events.jsonl", now_fn=_fixed_now())
    for i in range(count):
        log.append(
            "decision",
            "adopted",
            f"proposal:{i}",
            payload if payload is not None else {"action": f"act_{i}", "risk": 0.2 * i},
        )
    return log


def _lines(path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


class TestAuditChain:
    def test_append_chains_records(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        records = log.records()
        assert len(records) == 3
        assert [r.seq for r in records] == [0, 1, 2]
        assert records[0].prev_hash == ZERO_HASH
        assert records[1].prev_hash == records[0].hash
        assert records[2].prev_hash == records[1].hash
        assert log.verify().valid
        assert "chain intact" in log.verify().message

    def test_entity_types_are_validated(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl")
        with pytest.raises(ValueError):
            log.append("not_an_entity", "x", "id")
        with pytest.raises(TypeError):
            log.append("decision", "x", "id", payload="not a dict")

    def test_payload_is_canonicalised(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl", now_fn=_fixed_now())
        log.append(
            "decision", "adopted", "p:1", {"b": 1, "a": [3, {"d": 4, "c": 5}], "nan": float("nan")}
        )
        stored = log.records()[0].payload
        assert list(stored) == ["a", "b", "nan"]
        assert stored["a"] == [3, {"c": 5, "d": 4}]
        assert stored["nan"] == "nan"

    def test_payload_canonicalises_datetimes_sets_and_objects(self, tmp_path):
        import datetime as dt

        class Thing:
            def __repr__(self):
                return "<thing>"

        log = AuditLog(tmp_path / "e.jsonl", now_fn=_fixed_now())
        log.append(
            "identity",
            "commitment_changed",
            "id:1",
            {
                "when": dt.datetime(2026, 8, 11, 15, 0, tzinfo=dt.timezone.utc),
                "tags": {"c", "a", "b"},
                "thing": Thing(),
            },
        )
        stored = log.records()[0].payload
        assert stored["when"] == "2026-08-11T15:00:00+00:00"
        assert stored["tags"] == ["a", "b", "c"]
        assert stored["thing"] == "<thing>"

    def test_empty_log_verifies(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl")
        assert log.verify().valid
        assert len(log) == 0

    def test_missing_file_is_a_failure(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl")
        log.append("decision", "adopted", "proposal:0")
        (tmp_path / "e.jsonl").unlink()
        result = log.verify()
        assert not result.valid
        assert "missing" in result.message

    def test_batch_root_matches_tee_merkle(self, tmp_path):
        log = _make_log(tmp_path, count=4)
        expected = merkle_root([r.hash.encode("utf-8") for r in log.records()])
        assert log.batch_root() == expected
        assert isinstance(log.batch_root(), str) and len(log.batch_root()) == 64

    def test_anchor_persisted_outside_the_jsonl(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        anchor = tmp_path / "events.jsonl.root"
        assert anchor.exists()
        assert json.loads(anchor.read_text(encoding="utf-8"))["root"] == log.batch_root()
        # the anchor is a separate file from the chain
        assert anchor.read_text(encoding="utf-8") != log.path.read_text(encoding="utf-8")

    def test_anchor_updated_on_every_append(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        first_root = json.loads((tmp_path / "events.jsonl.root").read_text(encoding="utf-8"))[
            "root"
        ]
        log.append("veto", "applied", "proposal:2")
        second_root = json.loads((tmp_path / "events.jsonl.root").read_text(encoding="utf-8"))[
            "root"
        ]
        assert first_root != second_root
        assert second_root == log.batch_root()

    def test_empty_log_has_no_anchor_and_verifies(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl")
        assert not (tmp_path / "e.jsonl.root").exists()
        assert log.verify().valid

    def test_reproducible_across_identical_runs(self, tmp_path):
        first = _make_log(tmp_path, count=3)
        second_path = tmp_path / "second"
        second = AuditLog(second_path, now_fn=_fixed_now())
        for r in first.records():
            second.append(r.entity_type, r.event, r.entity_id, r.payload)
        assert _lines(first.path) == _lines(second_path)
        assert first.batch_root() == second.batch_root()

    def test_reopened_log_continues_the_chain(self, tmp_path):
        path = tmp_path / "events.jsonl"
        first = AuditLog(path, now_fn=_fixed_now())
        first.append("decision", "adopted", "proposal:0")
        first.append("decision", "adopted", "proposal:1")

        second = AuditLog(path, now_fn=_fixed_now())
        assert len(second) == 2  # chain restored from disk
        second.append("veto", "applied", "proposal:1")
        assert len(second) == 3
        assert [r.seq for r in second.records()] == [0, 1, 2]
        assert second.records()[2].prev_hash == second.records()[1].hash
        assert second.verify().valid
        # the file on disk is the ground truth: 3 records
        assert len(_lines(path)) == 3

    def test_reopen_batch_root_covers_loaded_chain(self, tmp_path):
        path = tmp_path / "events.jsonl"
        first = AuditLog(path, now_fn=_fixed_now())
        first.append("decision", "adopted", "proposal:0")
        second = AuditLog(path, now_fn=_fixed_now())
        assert second.batch_root() == first.batch_root()
        assert len(second.records()) == 1

    def test_reopen_rejects_malformed_store(self, tmp_path):
        path = tmp_path / "events.jsonl"
        first = AuditLog(path, now_fn=_fixed_now())
        first.append("decision", "adopted", "proposal:0")
        with path.open("a", encoding="utf-8") as fh:
            fh.write("not json\n")

        with pytest.raises(ValueError, match="malformed at record 1"):
            AuditLog(path)


class TestTamperDetection:
    def test_payload_mutation_reported_at_exact_index(self, tmp_path):
        log = _make_log(tmp_path, count=5)
        lines = _lines(log.path)
        mutated = json.loads(lines[2])
        mutated["payload"]["action"] = "malicious_action"
        lines[2] = json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        assert result.broken_index == 2
        assert "tampered" in result.message

    def test_hash_field_mutation_reported(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        lines = _lines(log.path)
        mutated = json.loads(lines[1])
        mutated["hash"] = "f" + mutated["hash"][1:]
        lines[1] = json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert result.broken_index == 1
        assert "tampered" in result.message

    def test_removed_record_breaks_chain_at_next_index(self, tmp_path):
        log = _make_log(tmp_path, count=5)
        lines = _lines(log.path)
        del lines[2]
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        # record at position 2 now carries seq 3: positional tamper at index 2
        assert result.broken_index == 2
        assert "positional" in result.message

    def test_inserted_record_breaks_chain(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        lines = _lines(log.path)
        forged = {
            "seq": 1,
            "entity_type": "decision",
            "event": "forged",
            "entity_id": "x",
            "timestamp": "2026-08-11T15:00:00.000Z",
            "payload": {},
            "prev_hash": ZERO_HASH,
            "hash": "0" * 64,
        }
        lines.insert(1, json.dumps(forged, sort_keys=True, separators=(",", ":")))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        # a well-formed forgery has an invalid content hash: caught at its own index
        assert result.broken_index == 1
        assert "tampered" in result.message

    def test_malformed_line_reported(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        lines = _lines(log.path)
        lines[1] = "this is not json"
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        assert result.broken_index == 1
        assert "malformed" in result.message

    def test_json_but_missing_keys_reported_malformed(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        lines = _lines(log.path)
        lines[1] = json.dumps({"seq": 1, "event": "partial"})
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = log.verify()
        assert result.broken_index == 1
        assert "malformed" in result.message

    def test_bad_types_reported_malformed(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        lines = _lines(log.path)
        mutated = json.loads(lines[1])
        mutated["seq"] = "one"  # non-int seq
        lines[1] = json.dumps(mutated)
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = log.verify()
        assert result.broken_index == 1
        assert "malformed" in result.message

    def test_rehashed_attack_breaks_chain_at_next_index(self, tmp_path):
        """An attacker who rewrites a record AND recomputes its hash correctly
        survives that record but must re-issue the next link: chain break."""
        log = _make_log(tmp_path, count=4)
        lines = _lines(log.path)
        mutated = json.loads(lines[2])
        mutated["payload"]["action"] = "evil"
        # Recompute the hash so record 2 itself verifies...
        import hashlib

        fields = {k: mutated[k] for k in mutated if k != "hash"}
        mutated["hash"] = hashlib.sha256(
            json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        lines[2] = json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        assert result.broken_index == 3  # record 3's prev_hash no longer matches
        assert "chain break" in result.message

    def test_append_after_tamper_still_caught(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        lines = _lines(log.path)
        mutated = json.loads(lines[1])
        mutated["event"] = "rewritten"
        lines[1] = json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        log.append("decision", "adopted", "proposal:99")
        result = log.verify()
        assert not result.valid
        assert result.broken_index == 1  # never silently revalidated

    def test_out_of_band_deletion_detected(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        log.path.unlink()
        result = log.verify()
        assert not result.valid
        assert "missing" in result.message

    def test_truncated_log_detected(self, tmp_path):
        log = _make_log(tmp_path, count=5)
        lines = _lines(log.path)
        log.path.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        assert result.broken_index == 3
        assert "truncated" in result.message

    def test_emptied_log_detected(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        log.path.write_text("", encoding="utf-8")

        result = log.verify()
        assert not result.valid
        assert "truncated" in result.message

    def test_full_rewrite_and_rehash_detected_by_anchor(self, tmp_path):
        """CWE-345: a writer that rewrites EVERY record and rehashes the whole
        chain passes all self-consistency rules but fails the anchor."""
        log = _make_log(tmp_path, count=4)
        forged_chain = []
        previous = ZERO_HASH
        for index in range(4):
            fields = {
                "seq": index,
                "entity_type": "decision",
                "event": "forged",
                "entity_id": f"proposal:{index}",
                "timestamp": "2026-08-11T15:00:00.000Z",
                "payload": {"action": "evil"},
                "prev_hash": previous,
            }
            import hashlib

            fields["hash"] = hashlib.sha256(
                json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            forged_chain.append(fields)
            previous = fields["hash"]
        log.path.write_text(
            "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in forged_chain)
            + "\n",
            encoding="utf-8",
        )

        result = log.verify()
        assert not result.valid
        assert "root mismatch" in result.message

    def test_anchor_deleted_detected(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        (tmp_path / "events.jsonl.root").unlink()
        result = log.verify()
        assert not result.valid
        assert "anchor" in result.message

    def test_record_without_anchor_update_detected(self, tmp_path):
        """Models the crash window (or a writer bypassing append()): a record
        lands in the JSONL but the anchor is not advanced — fail-loud."""
        log = _make_log(tmp_path, count=2)
        import hashlib

        fields = {
            "seq": 2,
            "entity_type": "decision",
            "event": "orphan",
            "entity_id": "proposal:2",
            "timestamp": "2026-08-11T15:00:00.000Z",
            "payload": {"action": "x"},
            "prev_hash": log.records()[-1].hash,
        }
        fields["hash"] = hashlib.sha256(
            json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        extra = json.dumps(fields, sort_keys=True, separators=(",", ":"))
        with log.path.open("a", encoding="utf-8") as fh:
            fh.write(extra + "\n")
        result = log.verify()
        assert not result.valid
        assert "root mismatch" in result.message


class TestAppendOnly:
    def test_no_mutation_api(self, tmp_path):
        log = _make_log(tmp_path, count=2)
        for forbidden in ("update", "delete", "rewrite", "truncate", "clear"):
            assert not hasattr(log, forbidden)
        with pytest.raises(AttributeError):  # frozen dataclass field
            log.records()[0].seq = 99

    def test_rewrite_attempt_is_detected(self, tmp_path):
        log = _make_log(tmp_path, count=4)
        lines = _lines(log.path)
        rewritten = json.loads(lines[2])
        rewritten["seq"] = 2
        rewritten["event"] = "forged_rewrite"
        lines[2] = json.dumps(rewritten, sort_keys=True, separators=(",", ":"))
        log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = log.verify()
        assert not result.valid
        assert result.broken_index == 2

    def test_verify_after_legitimate_appends_stays_valid(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        for i in range(3, 6):
            log.append("veto", "applied", f"proposal:{i}", {"reason": "safety"})
        assert log.verify().valid
        assert len(log) == 6


class TestSiemExport:
    def test_export_line_format(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        out = tmp_path / "events.syslog"
        count = log.export_siem(out)
        assert count == 3
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        for i, line in enumerate(lines):
            assert line.startswith("<13>1 2026-08-11T15:00:00.000Z - nomos ")
            assert f" {i} adopted " in line
            assert f'[nomos-audit entity_type="decision" entity_id="proposal:{i}" hash="' in line
        # payload JSON survives at the end of the line
        assert json.loads(lines[0].rsplit(" ", 1)[1]) == {"action": "act_0", "risk": 0.0}

    def test_export_is_deterministic(self, tmp_path):
        log = _make_log(tmp_path, count=3)
        out_a, out_b = tmp_path / "a.syslog", tmp_path / "b.syslog"
        log.export_siem(out_a)
        log.export_siem(out_b)
        assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")

    def test_sd_escaping(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl", now_fn=_fixed_now())
        log.append("identity", "commitment_changed", 'id"weird]\\x', {"k": "v"})
        out = tmp_path / "e.syslog"
        log.export_siem(out, hostname="node-1")
        line = out.read_text(encoding="utf-8").strip()
        assert line.startswith("<13>1 2026-08-11T15:00:00.000Z node-1 nomos 0 commitment_changed ")
        # RFC 5424 SD escaping: no raw quotes/brackets inside the SD element
        sd = line.split("] ", 1)[0].split("[", 1)[1]
        assert re.fullmatch(
            r'nomos-audit entity_type="identity" entity_id="id\\"weird\\\]\\\\x" hash="[0-9a-f]{64}"',
            sd,
        )


class TestPermissionsContract:
    def test_entity_types_are_the_documented_set(self):
        assert ENTITY_TYPES == ("proposal", "decision", "contract", "veto", "identity")

    def test_append_returns_verifiable_records(self, tmp_path):
        log = AuditLog(tmp_path / "e.jsonl", now_fn=_fixed_now())
        record = log.append("contract", "enacted", "contract:1", {"mask": {"bank_loans"}})
        assert isinstance(record, AuditRecord)
        assert isinstance(log.verify(), AuditVerification)
        assert log.verify().valid
