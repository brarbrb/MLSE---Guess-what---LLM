from .core_index import EmbedIndex
from .generator import ForbiddenAPI, GenConfig
from .vocabulary import WordSampler
import random

# Mocker for debugging purposes
# class WordLoader:
#     # for now something that mocks
#     def __init__(self):
#         # usuallly it initializes the WordSampler, embeddings, creates forbidden API and build vocabulary
#         # self.idx = EmbedIndex()
#         # self.api = ForbiddenAPI()
#         self.vocabulary = ["banana"]
    
#     def generate_target_word(self):
#         return random.choices(self.vocabulary)
    
#     def check_describtion(self): # for now all good
#         return True
    
#     def generate_forbidden_list(self, word):
#         return ["fruit", "bgvb", "banan"]


class WordLoader:
    """
    Singleton wrapper for the full LLM core.

    Usage:
        wl = WordLoader.get_instance()
        word = wl.generate_target_word()
        forb = wl.generate_forbidden_list(word)
        ok = wl.check_describtion(word, "a yellow fruit"(desc), forb)
    """
    _instance: "WordLoader | None" = None
    
    @classmethod
    def get_instance(cls):
        """
        Build or return the singleton.
        Call this at startup (e.g., before Flask app creation) to warm it up.
        """
        if cls._instance is not None:
            return cls._instance

        # --- Build the loader ---
        loader = cls()

        # Optional warmup
        try:
            sample = loader.generate_target_word()
            _ = loader.generate_forbidden_list(sample)
            print(sample, loader.check_describtion(sample, "short description", _))
            print("[llm-core] Initialized and warmed.")
        except Exception as e:
            print(f"[llm-core] Warmup failed: {e}")

        cls._instance = loader
        return loader

    # Regular init
    def __init__(self, llm_backend="ollama", llm_params={"model": "phi3:mini", "host": "http://localhost:11434"}):
        self.sampler = WordSampler()
        self.vocab = self.sampler.get_vocab()

        self.idx = EmbedIndex()
        self.idx.build(self.vocab)

        self.api = ForbiddenAPI(index=self.idx, llm_backend=llm_backend, llm_params=llm_params)
        self.vocabulary = ["banana"]
    
    def generate_target_word(self):
        """
        Pick a word from the sampler's vocabulary.
        Routes expect a single string.
        """
        word = self.sampler.random_word()
        return str(word)
    
    def check_describtion(self, word, description, forbidden): 
        # returns a list of issues found, empty if all good
        try:
            return self.api.check_description_llm(word, description, forbidden)
        except Exception:
            # If LLM not configured, just run the deterministic rules
            return self.api.check_description(word, description, forbidden)


    def generate_forbidden_list(self, word): 
        """
        Produce the final forbidden terms list for `word` using the full pipeline:
        FAISS neighbors + lexical expansions (+ optional LLM phrases), MMR rerank, dedupe/stemming.
        Returns lemma-form items.
        """
        terms = self.api.generate_forbidden(word)
        # Ensure list[str] even if backend returns tuples, empties etc.
        return [str(t) for t in terms if str(t).strip()]
    
