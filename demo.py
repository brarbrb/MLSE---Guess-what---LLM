# End-to-end demo for ForbiddenAPI (generator.py) with Ollama (Phi-3 Mini)
# Builds a vocab index, generates forbidden lists, validates sample descriptions.

from core_index import EmbedIndex
from generator import ForbiddenAPI, GenConfig
from vocabulary import WordSampler


# def build_vocab(n=80_000, min_len=3, max_len=14): #when submitting put n-larger #TODO: delete
#     raw = top_n_list("en", n=n)
#     vocab = [w for w in raw if w.isalpha() and min_len <= len(w) <= max_len]
#     # dedupe, preserve order
#     seen = set(); clean = []
#     for w in vocab:
#         if w not in seen:
#             seen.add(w); clean.append(w)
#     return clean

def main():
    print("[1/4] Building vocab…")
    sampler = WordSampler(seed=42) #TODO: remove before submission. 
    vocab = sampler.get_vocab()

    print("[2/4] Embedding & indexing (FAISS)…")
    idx = EmbedIndex()        # uses your sentence-transformer + FAISS (HNSW/Flat)
    idx.build(vocab)
    print(f"    Indexed {len(vocab):,} terms | dim={idx.dim}")

    print("[3/4] Creating ForbiddenAPI (Ollama: phi3:mini)…")
    api = ForbiddenAPI(
        index=idx,
        llm_backend="ollama",
        llm_params={"model": "phi3:mini", "host": "http://localhost:11434"},
        # config=GenConfig(  - I've already tuned it but it's possible to do it here if needed :) 
        #     faiss_topk=200,
        #     out_k=16,
        #     tau_close=0.70,
        #     tau_floor=0.30,
        #     tau_assoc=0.35,
        #     max_llm_terms_per_sense=4,
        #     max_llm_phrase_words=3,
        #     mmr_lambda=0.7
        # )
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
            verdict_hybrid = api.check_description_hybrid(word, text, banned)
            verdict_llm_only = api.check_description_llm(word, text, banned)
            print(f"DESC: “{text}”")
            print("Deterministic: ")
            print("  valid:", verdict["valid"], "| violations:", verdict["violations"])
            print("Hybrid: ")
            print("  valid:", verdict_hybrid["valid"], "| violations:", verdict_hybrid["violations"])
            print("LLM only" )
            print("  valid:", verdict_llm_only["valid"], "| violations:", verdict_llm_only["violations"])
        print()

if __name__ == "__main__":
    main()
