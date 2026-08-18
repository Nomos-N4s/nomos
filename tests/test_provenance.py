"""Pre-registration provenance must verify on any platform (#307)."""

import json
import os
import subprocess
import tempfile

from src.nomos.experiments.provenance import (
    commit_is_ancestor,
    content_digest,
    normalise,
    preregistration_provenance,
    verify_preregistration,
)
from src.nomos.experiments.rl_validate import validate_sweep

PREREG = "book/appendix-e-preregistration.md"


class TestNewlineNormalisation:
    def test_crlf_and_lf_agree(self):
        assert normalise(b"a\r\nb\r\n") == normalise(b"a\nb\n") == b"a\nb\n"

    def test_lone_cr_is_normalised(self):
        assert normalise(b"a\rb") == b"a\nb"

    def test_digest_is_independent_of_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            lf, crlf = os.path.join(d, "lf.md"), os.path.join(d, "crlf.md")
            with open(lf, "wb") as fh:
                fh.write(b"H4: bypass <= 0.05\nH5: ambiguous\n")
            with open(crlf, "wb") as fh:
                fh.write(b"H4: bypass <= 0.05\r\nH5: ambiguous\r\n")
            assert content_digest(lf) == content_digest(crlf)

    def test_digest_still_changes_with_content(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.md"), os.path.join(d, "b.md")
            with open(a, "w", newline="\n") as fh:
                fh.write("H4: bypass <= 0.05")
            with open(b, "w", newline="\n") as fh:
                fh.write("H4: bypass <= 0.50")
            assert content_digest(a) != content_digest(b)

    def test_missing_file_degrades_rather_than_raises(self):
        assert content_digest("book/does-not-exist.md") is None

    def test_matches_the_blob_git_stores(self):
        """The published `git show <rev>:<path> | sha256sum` must reproduce it.

        Compared against the blob rather than the working tree, so the property
        holds regardless of the checkout's line endings or uncommitted edits.
        """
        import hashlib

        blob = subprocess.run(
            ["git", "show", f"HEAD:{PREREG}"], capture_output=True, check=False
        ).stdout
        with tempfile.TemporaryDirectory() as d:
            # Simulate a CRLF checkout of exactly the bytes git stores.
            crlf = os.path.join(d, "checkout.md")
            with open(crlf, "wb") as fh:
                fh.write(blob.replace(b"\n", b"\r\n"))
            assert content_digest(crlf) == hashlib.sha256(blob).hexdigest()


class TestCommitReachability:
    def test_head_is_its_own_ancestor(self):
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip()
        assert commit_is_ancestor(head) is True

    def test_orphaned_commit_is_detected(self):
        # 6fde9c9 was rebased away; it is not reachable from main.
        assert commit_is_ancestor("6fde9c978e5699177f28c94a22320165ca4a9d4b") is False

    def test_unknown_revision_is_unknown_not_false(self):
        assert commit_is_ancestor("0" * 40) is None


class TestVerifyPreregistration:
    def test_the_real_provenance_verifies(self):
        assert verify_preregistration(preregistration_provenance()) == []

    def test_wrong_digest_is_caught(self):
        block = preregistration_provenance()
        block["sha256"] = "0" * 64
        problems = verify_preregistration(block)
        assert any("does not match" in p for p in problems)

    def test_unreachable_commit_is_caught(self):
        block = preregistration_provenance()
        block["commit"] = "6fde9c978e5699177f28c94a22320165ca4a9d4b"
        problems = verify_preregistration(block)
        assert any("not an ancestor" in p for p in problems)

    def test_missing_block_is_caught(self):
        assert verify_preregistration(None) == ["missing 'preregistration' provenance block"]

    def test_missing_digest_is_caught(self):
        problems = verify_preregistration({"path": PREREG, "sha256": None})
        assert any("unverifiable" in p for p in problems)

    def test_absent_file_is_not_reported_as_a_mismatch(self):
        """A checkout without the file is an unknown, not a falsified claim."""
        block = {"path": "book/does-not-exist.md", "sha256": "a" * 64}
        assert verify_preregistration(block) == []


class TestPublishedFrontierIsVerifiable:
    def test_committed_frontier_passes_validation(self):
        with open("book/appendix-f-data/verifier_frontier.json", encoding="utf-8") as fh:
            frontier = json.load(fh)
        assert validate_sweep(frontier) == []

    def test_committed_frontier_records_the_correction(self):
        with open("book/appendix-f-data/verifier_frontier.json", encoding="utf-8") as fh:
            pre = json.load(fh)["preregistration"]
        superseded = pre["correction"]["superseded"]
        # The superseded CRLF digest is retained rather than overwritten, and the
        # certified content digest stays checkable against the tag.
        assert superseded["sha256_as_recorded"].startswith("c6ea78a0")
        assert superseded["sha256_certified_content"].startswith("f0ce46a1")
        assert commit_is_ancestor(pre["commit"]) is True
