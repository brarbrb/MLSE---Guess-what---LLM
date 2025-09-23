import random
from typing import List, Optional
from wordfreq import top_n_list, zipf_frequency
from nltk.corpus import stopwords, words # to check that words are actual english words
import nltk

nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
STOPWORDS = set(stopwords.words("english"))

class WordSampler:
    def __init__(self,
                 n: int = 200_000,
                 min_len: int = 3,
                 max_len: int = 14,
                 min_zipf: float = 2.5,
                 max_zipf: float = 6.0,
                 seed: Optional[int] = None): # for testing
        """
        Build a clean vocabulary once and cache it.
        Arguments control how you filter the words.
        """
        self.rng = random.Random(seed)
        self.vocab = self._build_vocab(n, min_len, max_len, min_zipf, max_zipf)

    def _build_vocab(self,
                     n: int,
                     min_len: int,
                     max_len: int,
                     min_zipf: float,
                     max_zipf: float) -> List[str]:
        raw = top_n_list("en", n=n)
        vocab = []
        for w in raw:
            w = w.lower()
            if not w.isalpha():
                continue
            if w in STOPWORDS:
                continue
            if not (min_len <= len(w) <= max_len):
                continue
            z = zipf_frequency(w, "en")
            if not (min_zipf <= z <= max_zipf):
                continue
            vocab.append(w)

        # deleting duplicates
        seen = set()
        clean = []
        for w in vocab:
            if w not in seen:
                clean.append(w)
                seen.add(w)
        if not clean:
            raise ValueError("All words are used up:(")
        return clean
    
    def get_vocab(self):
        return self.vocab

    def random_word(self,
                    exclude: Optional[List[str]] = None) -> str:
        """
        Return a random word, excluding ones in the given list.
        Useful for skipping words already used by a player, that we can later generate using SQL tables
        """
        if exclude:
            candidates = [w for w in self.vocab if w not in exclude]
            if not candidates:
                raise ValueError("No words left after applying exclusions.")
            return self.rng.choice(candidates)
        return self.rng.choice(self.vocab)

# Demo
if __name__ == "__main__":
    sampler = WordSampler(seed=42)
    for _ in range(5):
        w = sampler.random_word()
        print(w, zipf_frequency(w, "en"))