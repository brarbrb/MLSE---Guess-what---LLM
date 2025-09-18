# End-to-end demo for ForbiddenAPI with Ollama (Phi-3 Mini)
# Builds a vocab index, generates forbidden lists, validates sample descriptions.

from wordfreq import top_n_list
from core_index import EmbedIndex
from generator import ForbiddenAPI, GenConfig


def build_vocab(n=80_000, min_len=3, max_len=14):
    raw = top_n_list("en", n=n)
    vocab = [w for w in raw if w.isalpha() and min_len <= len(w) <= max_len]
    # a few “giveaway” bigrams that make results feel human
    # vocab += [
    #     "ring of fire", "gas giant", "grand piano", "ash cloud",
    #     "money deposit", "savings account", "river bank", "fruit bat"
    # ]
    # dedupe, preserve order
    seen = set(); clean = []
    for w in vocab:
        if w not in seen:
            seen.add(w); clean.append(w)
    return clean

def main():
    print("[1/4] Building vocab…")
    vocab = build_vocab()

    print("[2/4] Embedding & indexing (FAISS)…")
    idx = EmbedIndex()        # uses your sentence-transformer + FAISS (HNSW/Flat)
    idx.build(vocab)
    print(f"    Indexed {len(vocab):,} terms | dim={idx.dim}")

    print("[3/4] Creating ForbiddenAPI (Ollama: phi3:mini)…")
    api = ForbiddenAPI(
        index=idx,
        llm_backend="ollama",
        llm_params={"model": "phi3:mini", "host": "http://localhost:11434"},
        config=GenConfig(
            faiss_topk=200,
            out_k=16,
            tau_close=0.70,
            tau_floor=0.30,
            tau_assoc=0.35,
            max_llm_terms_per_sense=4,
            max_llm_phrase_words=3,
            mmr_lambda=0.7
        )
    )

    print("[4/4] Generating lists & checking descriptions…\n")
    tests = {
        "bank": [
            ("A place for money deposit and savings", False),   # should violate
            ("Institution handling loans for customers", False),# likely violates
            ("Building with columns next to the museum", True), # might pass
        ],
        "bat": [
            ("A flying mammal that hunts insects at night", False), # likely violates
            ("Wooden club used in baseball", False),                 # likely violates
            ("Small animal sleeping in caves", False),               # likely violates
        ],
        "volcano": [
            ("A mountain that erupts with ash and lava", False),     # should violate
            ("Large hill near the coast", True),                     # may pass
            ("A geological vent releasing molten rock", False),      # likely violates
        ],
    }

    for word, samples in tests.items():
        print(f"=== {word.upper()} ===")
        banned = api.generate_forbidden(word, out_k=16)
        print("Forbidden (lemma form):")
        for t in banned:
            print("  -", t)

        for text, _ in samples:
            verdict = api.check_description(word, text, banned)
            print(f"DESC: “{text}”")
            print("  valid:", verdict["valid"], "| violations:", verdict["violations"])
        print()

if __name__ == "__main__":
    main()
