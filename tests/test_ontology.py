import pytest

from src.governance.identity.ontology import ActionBinding, Ontology, compute_hash


class TestComputeHash:
    def test_deterministic(self):
        h1 = compute_hash(b"hello")
        h2 = compute_hash(b"hello")
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        h1 = compute_hash(b"hello")
        h2 = compute_hash(b"world")
        assert h1 != h2

    def test_empty_bytes(self):
        h = compute_hash(b"")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_known_hash(self):
        h = compute_hash(b"test")
        assert h == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


class TestActionBinding:
    def test_frozen_dataclass(self):
        binding = ActionBinding(
            index=1, operation="move", runtime_hash="abc123", properties={"risk": 0.5}
        )
        assert binding.index == 1
        assert binding.operation == "move"
        assert binding.runtime_hash == "abc123"
        assert binding.properties == {"risk": 0.5}

    def test_frozen_cannot_modify(self):
        binding = ActionBinding(
            index=2, operation="jump", runtime_hash="def456", properties={}
        )
        with pytest.raises(Exception):
            binding.index = 99

    def test_properties_accessible(self):
        props = {"risk": 0.3, "reward": 1.0}
        binding = ActionBinding(index=0, operation="idle", runtime_hash="000", properties=props)
        assert binding.properties["risk"] == 0.3
        assert binding.properties["reward"] == 1.0


class TestOntology:
    def test_register_and_retrieve(self):
        o = Ontology()
        binding = o.register(1, "move", b"def move(): pass", {"risk": 0.1})
        assert binding.index == 1
        assert binding.operation == "move"
        assert len(binding.runtime_hash) == 64

    def test_register_duplicate_raises(self):
        o = Ontology()
        o.register(1, "move", b"code", {})
        with pytest.raises(ValueError, match="already bound"):
            o.register(1, "jump", b"code2", {})

    def test_verify_binding_match(self):
        o = Ontology()
        code = b"def move(): pass"
        o.register(1, "move", code, {})
        assert o.verify_binding(1, code) is True

    def test_verify_binding_mismatch(self):
        o = Ontology()
        o.register(1, "move", b"original", {})
        assert o.verify_binding(1, b"modified") is False

    def test_verify_binding_not_found(self):
        o = Ontology()
        assert o.verify_binding(99, b"anything") is False

    def test_get_properties_found(self):
        o = Ontology()
        o.register(1, "move", b"code", {"risk": 0.5, "reward": 1.0})
        props = o.get_properties(1)
        assert props == {"risk": 0.5, "reward": 1.0}

    def test_get_properties_not_found(self):
        o = Ontology()
        assert o.get_properties(99) is None

    def test_get_properties_returns_copy(self):
        o = Ontology()
        o.register(1, "move", b"code", {"risk": 0.5})
        props = o.get_properties(1)
        props["risk"] = 0.9
        assert o.get_properties(1)["risk"] == 0.5

    def test_has_index(self):
        o = Ontology()
        o.register(1, "move", b"code", {})
        assert o.has_index(1) is True
        assert o.has_index(2) is False

    def test_size(self):
        o = Ontology()
        assert o.size == 0
        o.register(1, "a", b"code1", {})
        o.register(2, "b", b"code2", {})
        assert o.size == 2

    def test_append_only_log(self):
        o = Ontology()
        b1 = o.register(1, "a", b"code1", {})
        b2 = o.register(2, "b", b"code2", {})
        assert o._append_only_log == [b1, b2]

    def test_repr(self):
        o = Ontology()
        o.register(1, "a", b"code", {})
        assert repr(o) == "<Ontology 1 actions>"
