from generator import tokenize, lemmatize_term, stem_of, stem_bag
from generator import ForbiddenAPI, GenConfig, LLMClient
from vocabulary import WordSampler

import numpy as np
import itertools
import pytest
import types


# ---- Tiny fake SentenceTransformer-like model & FAISS-like index ----
class _TinyModel:
    def __init__(self, table):
        # table: {term: np.array([...], dtype=float32)}
        self._table = table
        self._dim = len(next(iter(table.values())))
    def get_sentence_embedding_dimension(self):
        return self._dim
    def encode(self, texts, normalize_embeddings=True, convert_to_numpy=True):
        if isinstance(texts, str):
            texts = [texts]
        vecs = []
        for t in texts:
            v = self._table.get(t, None)
            if v is None:
                # OOV => small random but stable direction by hash
                rng = np.random.default_rng(abs(hash(t)) % (2**32))
                v = rng.normal(size=self._dim).astype("float32")
            vecs.append(v)
        V = np.stack(vecs).astype("float32")
        if normalize_embeddings:
            n = np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
            V = V / n
        return V

class TinyIndex:
    """
    Minimal drop-in for EmbedIndex used inside tests.
    Fields expected by generator.ForbiddenAPI:
      - model (with .encode and .get_sentence_embedding_dimension)
      - dim
      - items
      - vecs
      - search(queries, k) -> (sims, idxs)
    """
    def __init__(self, table, items):
        self.model = _TinyModel(table)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.items = items[:]
        self.vecs = self.model.encode(items, True, True).astype("float32")

    def search(self, queries, k):
        Q = self.model.encode(queries, True, True).astype("float32")  # (q,d)
        S = Q @ self.vecs.T                                           # cosine
        # top-k indices per row
        idxs = np.argsort(-S, axis=1)[:, :k]
        sims = np.take_along_axis(S, idxs, axis=1)
        return sims.astype("float32"), idxs.astype("int64")

@pytest.fixture
def tiny_vocab():
    # small controlled space
    return [
        "volcano", "lava", "ash", "eruption", "ring of fire",
        "bank", "money", "loan", "river", "bat", "mammal", "baseball",
        "fire", "mountain", "vent", "deposit", "account"
    ]

@pytest.fixture
def tiny_vectors(tiny_vocab):
    # Handcraft simple directions: group related words near each other.
    def unit(*coords):
        v = np.array(coords, dtype="float32")
        v /= (np.linalg.norm(v) + 1e-9)
        return v

    # 5D toy embedding space
    V = {
        # volcano cluster
        "volcano":      unit(1, 0.9, 0.8, 0, 0),
        "lava":         unit(1, 0.8, 0.7, 0, 0),
        "ash":          unit(0.9, 0.7, 0.6, 0, 0),
        "eruption":     unit(0.95, 0.85, 0.75, 0, 0),
        "ring of fire": unit(0.85, 0.65, 0.55, 0, 0),
        "mountain":     unit(0.7, 0.5, 0.4, 0, 0),
        "vent":         unit(0.8, 0.6, 0.5, 0, 0),
        "fire":         unit(0.6, 0.5, 0.5, 0, 0),

        # bank cluster
        "bank":         unit(0, 0, 0, 1, 0.9),
        "money":        unit(0, 0, 0, 0.95, 0.8),
        "loan":         unit(0, 0, 0, 0.9, 0.75),
        "deposit":      unit(0, 0, 0, 0.92, 0.78),
        "account":      unit(0, 0, 0, 0.88, 0.7),
        "river":        unit(0, 0.1, 0.1, 0.2, 0.05),  # weak tie

        # bat cluster
        "bat":          unit(0, 1, 0.8, 0, 0),
        "mammal":       unit(0, 0.9, 0.7, 0, 0),
        "baseball":     unit(0, 0.7, 0.5, 0, 0),
    }
    # ensure all vocab keys exist
    for w in tiny_vocab:
        V.setdefault(w, unit(0,0,0,0,0.1))
    return V

@pytest.fixture
def tiny_index(tiny_vectors, tiny_vocab):
    return TinyIndex(tiny_vectors, tiny_vocab)



# tests/test_text_utils.py
def test_tokenize_basic():
    assert tokenize("A mountain that erupts!") == ["a","mountain","that","erupts"]

def test_lemmatize_term_phrase():
    assert lemmatize_term("eruptions happening") == "eruption happening"

def test_stem_of_single_and_phrase():
    assert stem_of("volcanoes") == stem_of("volcano")
    s1 = stem_bag("ring of fires")
    s2 = stem_bag("ring fire")
    # overlapping stems not empty
    assert len(s1.intersection(s2)) >= 1



def test_check_description_rules_phrase_and_target(tiny_index):
    api = ForbiddenAPI(index=tiny_index, llm_backend=None, config=GenConfig())
    forbidden = ["ring of fire", "lava"]  # already lemma-form is fine

    # phrase + lemma + target-stem
    text = "The volcanoes formed a ring of fire with lava flows."
    verdict = api.check_description("volcano", text, forbidden)

    kinds = {rule for _, rule in verdict["violations"]}
    spans = {span.lower() for span, _ in verdict["violations"]}
    assert "phrase-forbidden" in kinds
    assert "lemma-forbidden" in kinds or "banned-stem-forbidden" in kinds
    assert "target-stem-forbidden" in kinds
    assert "ring of fire" in spans
    assert "volcanoes" in spans or "volcano" in spans
    assert verdict["valid"] is False

def test_check_description_passes_when_clean(tiny_index):
    api = ForbiddenAPI(index=tiny_index, llm_backend=None, config=GenConfig())
    forbidden = ["ring of fire", "lava"]
    text = "A large hill near the coast with hiking trails."
    verdict = api.check_description("volcano", text, forbidden)
    assert verdict["valid"] is True
    assert verdict["violations"] == []
    
    
# tests/test_hybrid_merge.py
def test_hybrid_merges_and_deduplicates(monkeypatch, tiny_index):
    api = ForbiddenAPI(index=tiny_index, llm_backend=None, config=GenConfig())

    # Stub deterministic checker to return one violation
    def fake_det(word, desc, forbidden):
        return {"valid": False, "violations": [("lava", "lemma-forbidden")]}

    # Stub LLM phase to return a different rule for same span + one new entry
    def fake_llm(word, desc, forbidden, max_findings=10):
        return {"valid": False, "violations": [
            ("LAVA", "lemma-forbidden"),                 # same span (case-insensitive), same rule -> dedup
            ("l a v a", "spelling-circumvention")       # new unique key
        ]}

    api.check_description = fake_det  # patch method
    api.check_description_llm = fake_llm
    api.llm = object()                # truthy => LLM branch used

    merged = api.check_description_hybrid("volcano", "text", ["lava"], use_llm=True)
    assert merged["valid"] is False
    # Should have 2 unique violations after dedup
    assert len(merged["violations"]) == 2
    keys = {(s.lower(), r) for s, r in merged["violations"]}
    assert ("lava", "lemma-forbidden") in keys
    assert ("l a v a", "spelling-circumvention") in keys


# tests/test_generate_forbidden.py
def test_generate_forbidden_happy_path(monkeypatch, tiny_index):
    cfg = GenConfig(faiss_topk=10, out_k=5, tau_assoc=0.1, tau_floor=0.0, mmr_lambda=0.7)
    api = ForbiddenAPI(index=tiny_index, llm_backend=None, config=cfg)

    # Patch out the parts that would hit WordNet/FAISS/LLM
    monkeypatch.setattr(api, "meaning_queries", lambda w: (["volcano", "volcano — a mountain that erupts"], ["def1"]))
    monkeypatch.setattr(api, "faiss_neighbors", lambda Q, k: {"lava", "ash", "eruption", "mountain"})
    monkeypatch.setattr(api, "expand_lexical", lambda w: ({"s": {"eruption"}}, {"s": set()}))
    # Pretend LLM suggested phrases (but we're not enabling llm in api)
    llm_terms = {"ring of fire"}
    monkeypatch.setattr(api, "cos_w", lambda w, t: 0.9)  # keep everything

    # Inject llm_terms into rank_pool call via monkeypatching method wrapper
    real_rank_pool = api.rank_pool
    def wrapped_rank_pool(w, pool, syns, ants, _llm_terms_unused):
        return real_rank_pool(w, pool, syns, ants, llm_terms)
    monkeypatch.setattr(api, "rank_pool", wrapped_rank_pool)

    out = api.generate_forbidden("volcano", out_k=5)
    # Expectations:
    assert "volcano" not in out                    # target excluded
    assert any(t in out for t in ["lava", "ash", "eruption", "ring of fire"])
    # No duplicate stems (MMR stem-guard)
    stems = set()
    from generator import stem_of
    for t in out:
        st = stem_of(t)
        assert st not in stems
        stems.add(st)


# tests/test_llmclient_parsing.py
class _Resp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self): pass
    def json(self):
        return self._payload

def test_llmclient_accepts_array_string(monkeypatch):
    def fake_post(url, json, timeout):
        # Ollama returns {"response": '["ring of fire","fire mountain"]'}
        return _Resp({"response": '["ring of fire", "fire mountain"]'})
    monkeypatch.setattr("generator.requests.post", fake_post)

    llm = LLMClient(backend="ollama", llm_params={"model": "fake", "host": "http://x"})
    out = llm.propose_phrases("volcano", "def", 4, 3)
    assert out == ["ring of fire", "fire mountain"]

def test_llmclient_accepts_dict_terms(monkeypatch):
    def fake_post(url, json, timeout):
        return _Resp({"response": '{"terms":["ring of fire","fire mountain"]}'})
    monkeypatch.setattr("generator.requests.post", fake_post)

    llm = LLMClient(backend="ollama", llm_params={"model": "fake"})
    out = llm.propose_phrases("volcano", None, 4, 3)
    assert out == ["ring of fire", "fire mountain"]

def test_llmclient_fallback_on_fenced_json(monkeypatch):
    body = "```json\n[\"ring of fire\", \"fire mountain\"]\n```"
    def fake_post(url, json, timeout):
        return _Resp({"response": body})
    monkeypatch.setattr("generator.requests.post", fake_post)

    llm = LLMClient(backend="ollama", llm_params={"model": "fake"})
    out = llm.propose_phrases("volcano", None, 4, 3)
    assert out == ["ring of fire", "fire mountain"]


# tests/test_vocabulary.py
def test_word_sampler_deterministic_with_seed():
    s1 = WordSampler(seed=123)
    s2 = WordSampler(seed=123)
    seq1 = [s1.random_word() for _ in range(5)]
    seq2 = [s2.random_word() for _ in range(5)]
    assert seq1 == seq2

def test_word_sampler_exclude_list():
    s = WordSampler(seed=123)
    ex = [s.random_word() for _ in range(10)]
    w = s.random_word(exclude=ex)
    assert w not in ex
    
    
class _LLMDummy:
    def __init__(self, backend="ollama", params=None):
        self.backend = backend
        self.params = params or {}

def test_check_description_llm_parsing(monkeypatch):
    api = ForbiddenAPI()
    api.llm = _LLMDummy(backend="ollama", params={"model":"fake","host":"http://x"})

    class _Resp:
        def __init__(self, payload): self._payload = payload
        def json(self): return self._payload

    # Emulate a neat JSON array string reply
    def fake_post(url, json=None, timeout=60):
        return _Resp({"response": '[{"span":"l a v a","rule":"spelling-circumvention"}]'})

    monkeypatch.setattr("checker_suggestions.requests.post", fake_post)

    out = api.check_description_llm("volcano", "l a v a everywhere", ["lava"], max_findings=5)
    assert out["valid"] is False
    assert ("l a v a", "spelling-circumvention") in out["violations"]

def test_check_description_hybrid_merge(monkeypatch):
    api = ForbiddenAPI()
    api.llm = _LLMDummy()

    def det(word, desc, forbidden):
        return {"valid": False, "violations": [("lava", "lemma-forbidden")]}

    def llm(word, desc, forbidden, max_findings=10):
        return {"valid": False, "violations": [("LAVA", "lemma-forbidden"), ("l a v a", "spelling-circumvention")]}

    monkeypatch.setattr(api, "check_description", det)
    monkeypatch.setattr(api, "check_description_llm", llm)

    merged = api.check_description_hybrid("volcano", "xx", ["lava"], use_llm=True)
    assert len(merged["violations"]) == 2