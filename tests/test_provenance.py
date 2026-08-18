"""Pre-registration provenance must verify on any platform (#307)."""

import json
import os
import subprocess
import tempfile

import pytest

from src.nomos.experiments.provenance import (
    commit_is_ancestor,
    commit_touched_path,
    content_digest,
    normalise,
    preregistration_provenance,
    repo_root,
    resolve,
    verify_preregistration,
)
from src.nomos.experiments.rl_validate import validate_sweep

PREREG = "book/appendix-e-preregistration.md"


@pytest.fixture
def orphan_repo():
    """A throwaway repo containing a commit unreachable from HEAD.

    Built rather than borrowed from this repository's own history: CI checks out
    shallow, so real commits may be absent and ancestry becomes *unknown* rather
    than false. The distinction is the point of the test, so it needs a history
    it controls.
    """
    with tempfile.TemporaryDirectory() as d:
        repo = os.path.join(d, "repo")
        os.makedirs(repo)

        def git(*args):
            return subprocess.run(
                ["git", *args], cwd=repo, capture_output=True, text=True, check=True
            )

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        with open(os.path.join(repo, "prereg.md"), "wb") as fh:
            fh.write(b"H4: bypass <= 0.05\n")
        git("add", "prereg.md")
        git("commit", "-q", "-m", "certify")
        head = git("rev-parse", "HEAD").stdout.strip()

        git("checkout", "-q", "-b", "side")
        with open(os.path.join(repo, "other.md"), "wb") as fh:
            fh.write(b"unmerged\n")
        git("add", "other.md")
        git("commit", "-q", "-m", "orphan")
        orphan = git("rev-parse", "HEAD").stdout.strip()
        git("checkout", "-q", "main")

        cwd = os.getcwd()
        os.chdir(repo)
        try:
            yield {"head": head, "orphan": orphan, "repo": repo}
        finally:
            os.chdir(cwd)


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

    def test_orphaned_commit_is_detected(self, orphan_repo):
        assert commit_is_ancestor(orphan_repo["orphan"]) is False
        assert commit_is_ancestor(orphan_repo["head"]) is True

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

    def test_unreachable_commit_is_caught(self, orphan_repo):
        block = preregistration_provenance("prereg.md")
        assert block["sha256"] is not None
        block["commit"] = orphan_repo["orphan"]
        problems = verify_preregistration(block)
        assert any("not an ancestor" in p for p in problems)

    def test_missing_block_is_caught(self):
        assert verify_preregistration(None) == ["missing 'preregistration' provenance block"]

    def test_missing_digest_is_caught(self):
        problems = verify_preregistration({"path": PREREG, "sha256": None})
        assert any("unverifiable" in p for p in problems)

    def test_unreadable_file_is_reported_not_passed_over(self):
        """An unverifiable claim must not look identical to a verified one."""
        block = {"path": "book/does-not-exist.md", "sha256": "a" * 64}
        problems = verify_preregistration(block)
        assert any("cannot be verified" in p for p in problems)

    def test_reachable_but_unrelated_commit_is_rejected(self):
        """Reachability alone would let any ancestor supply the date."""
        other = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "src/nomos/identity/keys.py"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        block = preregistration_provenance()
        block["commit"] = other
        problems = verify_preregistration(block)
        assert any("never modified" in p for p in problems)

    def test_missing_commit_is_reported(self):
        block = preregistration_provenance()
        block["commit"] = None
        problems = verify_preregistration(block)
        assert any("commit is missing" in p for p in problems)


class TestPathResolution:
    """Provenance must describe the repository, not the caller's working directory."""

    def test_resolve_anchors_relative_paths_at_the_repo_root(self):
        root = repo_root()
        assert root is not None
        assert os.path.abspath(resolve(PREREG)) == os.path.abspath(os.path.join(root, PREREG))

    def test_absolute_paths_pass_through(self):
        assert resolve(os.path.abspath(PREREG)) == os.path.abspath(PREREG)

    def test_digest_is_identical_from_a_subdirectory(self):
        expected = content_digest(PREREG)
        cwd = os.getcwd()
        os.chdir(os.path.join(cwd, "src"))
        try:
            assert content_digest(PREREG) == expected
        finally:
            os.chdir(cwd)

    def test_verification_holds_from_a_subdirectory(self):
        block = preregistration_provenance()
        cwd = os.getcwd()
        os.chdir(os.path.join(cwd, "tests"))
        try:
            assert verify_preregistration(block) == []
        finally:
            os.chdir(cwd)


class TestCommitBinding:
    def test_certifying_commit_modified_the_document(self, orphan_repo):
        assert commit_touched_path(orphan_repo["head"], "prereg.md") is True

    def test_commit_that_touched_another_file_is_not_bound(self, orphan_repo):
        assert commit_touched_path(orphan_repo["orphan"], "prereg.md") is False

    def test_unknown_revision_is_unknown(self):
        assert commit_touched_path("0" * 40, PREREG) is None


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
        # None on a shallow clone (the object is absent) - but never provably
        # unreachable, which is the defect this replaced.
        assert commit_is_ancestor(pre["commit"]) is not False
