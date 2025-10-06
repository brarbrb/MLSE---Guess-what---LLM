"""API-style module for building forbidden lists and validating descriptions.
Pipeline: Retrieval (FAISS) + LLM (constrained) + lexical expansions + MMR rerank.

Requirements:
  pip install faiss-cpu sentence-transformers nltk wordfreq requests(for LLM)
  python -m nltk.downloader wordnet omw-1.4 punkt

Usage example:
  from core_index import EmbedIndex
  from generator import ForbiddenAPI, GenConfig

  idx = EmbedIndex()             # you build this elsewhere (core_index)
  idx.build(vocab)               # vocab = list[str]

  api = ForbiddenAPI(index=idx, llm_backend="ollama",
                     llm_params={"model": "llama3.2:3b-instruct", "host": "http://localhost:11434"})

  banned = api.generate_forbidden("bank", out_k=16)
  verdict = api.check_description("bank", "A place for money savings", banned)
  print(banned)
  print(verdict)"""


from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass # easy to tune configurations 
import re # basic pacage for working with text
import numpy as np
import re, requests, json # for prompting  

from nltk.corpus import wordnet as wn # for working with synsets (antonyms, description, synonyms etc.)
from nltk.stem import WordNetLemmatizer # for working with same-stem words
from nltk.stem import SnowballStemmer

from .core_index import EmbedIndex # used only for defining the type of parmeter in function
from typing import Dict, List, Tuple


@dataclass
class GenConfig:
    """
    To adjust strictness raise/lower tau_close, tau_floor, tau_assoc, and mmr_lambda in GenConfig.
    this is used in our ForbiddenAPI module 
    """
    # Retrieval sizes / thresholds
    faiss_topk: int = 200 # how many similiar items to retrieve, larger k less chances we miss something 
    # Note: we will filter this k=200 by similiar stemms so it in fact will reslut in less than 200 to choose from
    out_k: int = 16 # the size of the list
    tau_close: float = 0.70   # synonyms "very close" threshold
    tau_floor: float = 0.30   # drop neighbors below this (except antonyms)
    tau_assoc: float = 0.35   # keep LLM phrases only if cosine >= tau_assoc
    max_llm_terms_per_sense: int = 4  # cap per sense to avoid drift
    max_llm_phrase_words: int = 3     # keep phrases up to 3 words

    # MMR diversification (relevance vs diversity)
    mmr_lambda: float = 0.7

    # Scoring weights
    w_cos: float = 1.0
    w_syn: float = 0.6
    w_ant: float = 0.5
    w_llm: float = 0.2
    w_colloc: float = 0.15  # placeholder for PMI if we later add it
    # If later we add a feature for how often two words appear together
    # PMI weight tells how much that feature matters in ranking forbidden terms
    # really don't know if needed, probably we anyway will find it 
    # this is good for cases like "volcano" "erruption": these words are very likely to come together -> higher PMI


# ---------- LLM client (currently Ollama compatible) ----------
class LLMClient:
    """
    Minimal LLM adapter. Pick backend: "ollama" or None. 
    - Ollama: llm_params = {"model": "llama3.2:3b-instruct", "host": "http://localhost:11434"}
    """
    def __init__(self, backend: Optional[str] = None, llm_params: Optional[dict] = None):
        self.backend = backend # what type of model is used - to select correct api calls
        self.params = llm_params or {}
    
    def propose_phrases(self, word: str, gloss: Optional[str], k: int, max_words: int) -> List[str]:
        """
        Return short 'giveaway' phrases. Prefer strict JSON via Ollama's format='json'.
        Falls back to extracting the first JSON array if the model misbehaves.
        """
        if not self.backend:
            return []

        sense_hint = f' (sense: "{gloss}")' if gloss else ""
        # Keep it *very* explicit. Models still sometimes chat; we sanitize below.
        prompt = (
            f'Return ONLY a JSON array of 3-{k} short "forbidden" clue terms for "{word}"{sense_hint}. '
            f'Each item is a string (max {max_words} words). '
            f'Do NOT include the target word, stopwords, or explanations.'
        )

        if self.backend == "ollama":
            host = self.params.get("host", "http://localhost:11434")
            model = self.params["model"]

            # ① Ask Ollama to enforce JSON
            payload = {
                "model": model,
                "prompt": prompt,
                "temperature": 0.0,
                "stream": False,
                "format": "json",          # <- forces the model to emit valid JSON
                "options": {"num_ctx": 2048}
            }
            resp = requests.post(f"{host}/api/generate", json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json().get("response", "")

            # Sometimes Ollama already returns a parsed JSON object/string. Handle both.
            arr = None
            if isinstance(text, list):
                arr = text
            elif isinstance(text, str):
                # ② First try strict parse
                try:
                    arr = json.loads(text)
                except Exception:
                    # Fallback: strip fences and fish out the first [...] block
                    # Remove ```...``` fences if present
                    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
                    # Grab the first JSON array non-greedily
                    m = re.search(r"\[[\s\S]*?\]", fenced)
                    if m:
                        try:
                            arr = json.loads(m.group(0))
                        except Exception:
                            arr = None

            if arr is None:
                # As a last resort, return empty — we'll just rely on non-LLM signals
                return []

            # The model sometimes returns {"terms": [...]} — normalize that.
            if isinstance(arr, dict) and "terms" in arr and isinstance(arr["terms"], list):
                arr = arr["terms"]

            # Keep only non-empty strings, lowercased
            return [s.strip().lower() for s in arr if isinstance(s, str) and s.strip()]

        # Other backends (not used right now)
        return []


    # def propose_phrases(self, word: str, gloss: Optional[str], k: int, max_words: int) -> List[str]:
    #     """
    #     params: 
    #     word - target word in base lema form after text "normalization" 
    #     gloss - specific meaning of the word (we get it from nltk)
    #     k - how many proposes to return (for each term). In configuration it's max_llm_terms_per_sense
    #     max_words - in configurations: max_llm_phrase_words - how many words for each proposal 
    #     returns a list that contains proosed words by llm
    #     """
    #     if not self.backend:
    #         return []

    #     # Short, constrained prompt; enforce JSON array only.
    #     sense_hint = f' (sense: "{gloss}")' if gloss else ""
    #     prompt = (
    #         f'Return a JSON array (no prose) of 3-{k} short "forbidden" clue terms for the word "{word}"{sense_hint}. '
    #         f'Include near-synonyms and commonsense giveaway phrases (max {max_words} words per item). '
    #         f'Do NOT include the word itself or trivial stopwords. JSON array ONLY.'
    #     )

    #     if self.backend == "ollama":
    #         host = self.params.get("host", "http://localhost:11434")
    #         model = self.params["model"]
    #         resp = requests.post(
    #             f"{host}/api/generate",
    #             json={"model": model, "prompt": prompt, "temperature": 0.2, "stream": False, "options": {"num_ctx": 2048}},
    #             timeout=60
    #         )
    #         text = resp.json()["response"].strip()
    #         print("the response of the LLM is: ", text) # testing TODO
    #         try:
    #             arr = json.loads(text)
    #         except Exception:
    #             print("FLAG in propose phrases") # testing TODO
    #             # Fallback parse: first [...] block
    #             start, end = text.find("["), text.rfind("]")
    #             arr = json.loads(text[start:end+1]) if start != -1 and end != -1 else []
    #         return [t.strip().lower() for t in arr if isinstance(t, str) and t.strip()]
    #     print("None was added by llm") # testing TODO
    #     return []



# ---------- Utility: text normalization ----------
"""this step includes Lematizing - bringing all the words to one unified form - lemma 
(different from stem, since stem a lot of times can be umeaningful word)
stemming used for removing from suggested lists of forbidden words same-stem words, 
it also used for validity of description checks
"""

_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)

def tokenize(text: str) -> List[str]:
    return _WORD.findall(text.lower())

LEMMATIZER = WordNetLemmatizer() 
STEMMER = SnowballStemmer("english")

def lemmatize_term(term: str) -> str:
    # Lemmatize each token in a phrase; rejoin with space.
    toks = tokenize(term)
    lemmas = [LEMMATIZER.lemmatize(t) for t in toks]
    return " ".join(lemmas)

def stem_of(term: str) -> str:
    toks = tokenize(term)
    stems = [STEMMER.stem(t) for t in toks]
    return " ".join(stems)

def stem_bag(term: str) -> set:
    """Return the set of token stems in a term (phrase-safe)."""
    return {STEMMER.stem(t) for t in tokenize(term)}


# ---------- Core API ----------
class ForbiddenAPI:
    """
    - generate_forbidden(word): returns a *lemma-form* list of forbidden terms (excludes same-stem words as target)
    - check_description(word, description, forbidden): validates a description under the game rules
    """
    def __init__(self, index: EmbedIndex, llm_backend: Optional[str] = None, llm_params: Optional[dict] = None, config: GenConfig = GenConfig()):
        self.idx = index
        self.cfg = config
        self.llm = LLMClient(llm_backend, llm_params) if llm_backend else None
        # saves embeddings so we don’t re-compute the same word vector again and again.
        self._enc_cache: Dict[str, np.ndarray] = {}

    # --------- Public: forbidden list generation ---------
    def generate_forbidden(self, word: str, out_k: Optional[int] = None) -> List[str]:
        w = word.lower().strip()
        out_k = out_k or self.cfg.out_k

        queries, senses = self.meaning_queries(w) # collecting all possible meanings 
        cand = self.faiss_neighbors(queries, self.cfg.faiss_topk) # effective search of closest words to the meaning 
        
        syn_by_sense, ant_by_sense = self.expand_lexical(w) # lexical expansions (synonyms/antonyms per sense)
        syns = set().union(*syn_by_sense.values()) if syn_by_sense else set()
        ants = set().union(*ant_by_sense.values()) if ant_by_sense else set()

        llm_terms = []
        if self.llm:
            # loop that generates LLM based phrases per each sense (constrained)
            # they are filtered by cosine similiarity to ensure close and not too far away responses(words)
            for gloss in senses:
                props = self.llm.propose_phrases(
                    word=w,
                    gloss=gloss,
                    k=self.cfg.max_llm_terms_per_sense,
                    max_words=self.cfg.max_llm_phrase_words
                )
                # similarity filter to avoid drift
                kept = [t for t in props if self.cos_w(w, t) >= self.cfg.tau_assoc and len(tokenize(t)) <= self.cfg.max_llm_phrase_words]
                llm_terms.extend(kept)

        # assemble pool
        # NOTE: we do not include same-stem words in the final list as it's expected from the rules of the games
        pool = set()
        # |=  easy way to do union on sets :) 
        pool |= cand # candidates from index search of closely related words
        pool |= syns # adding synonyms and antonyms
        pool |= ants
        pool |= set(llm_terms) 

        # normalize all proposes to lemma form in the final output space
        pool = {lemmatize_term(t) for t in pool if t and t != w}
        # remove items with same stem as the target
        target_stem = stem_of(w)
        pool = {t for t in pool if stem_of(t) != target_stem and t}     
        
        # scoring & MMR selection
        ranked = self.rank_pool(w, pool, syns, ants, set(llm_terms))
        final = self.mmr_select(ranked, out_k) # removing stem overlap between the items thmdelves 

        return final

    # --------- Public: description validation ---------
    # TODO: Not sure of this function, probably will change it !
    def check_description(self, word: str, description: str, forbidden: List[str]) -> Dict:
        """
        Enforces:
          - The target word and ANY same-stem variants are forbidden in the description.
          - Any term from the final forbidden list (lemma-form) is forbidden.
          - Any same-stem variant of a forbidden term is also forbidden.
          - Multi-word phrases in the forbidden list are matched as whole-phrase (case-insensitive).
        Returns dict with 'valid': bool, 'violations': List[Tuple[str, str]] where (match, rule).
        """
        w = word.lower().strip()
        text = description.lower()

        # Precompute banned lemmas & stems
        banned_lemmas = {lemmatize_term(t) for t in forbidden}
        banned_stems = {stem_of(t) for t in banned_lemmas}
        target_stem = stem_of(w)

        violations: List[Tuple[str, str]] = []

        # Phrase-level checks (if a word in forbidden list has few words)
        phrases = [t for t in banned_lemmas if " " in t] 
        for p in phrases:
            # word-boundary regex for the exact phrase (lemmatized form)
            pattern = r"\b" + re.escape(p) + r"\b"
            if re.search(pattern, text):
                violations.append((p, "phrase-forbidden"))

        # Token-level checks (lemmas + stems)
        toks = tokenize(text)
        # stem/lemma each token
        for tok in toks:
            tok_lemma = LEMMATIZER.lemmatize(tok)
            tok_stem = STEMMER.stem(tok)

            # Target and same-stem variants
            if tok_stem == target_stem:
                violations.append((tok, "target-stem-forbidden"))
                continue

            # Direct lemma banned
            if tok_lemma in banned_lemmas:
                violations.append((tok, "lemma-forbidden"))
                continue

            # Same-stem as any banned term
            if tok_stem in banned_stems:
                violations.append((tok, "banned-stem-forbidden"))
                continue

        return {"valid": len(violations) == 0, "violations": violations}
    
    def check_description_llm(
        self,
        word: str,
        description: str,
        forbidden: List[str],
        max_findings: int = 10
    ) -> Dict:
        """
        LLM adjudicator for semantic/obfuscation violations.
        Returns {"valid": bool, "violations": [(span, rule)]}.
        Requires self.llm to be configured (ollama/openai).
        """
        if not self.llm:
            return {"valid": True, "violations": []}

        w = word.lower().strip()
        desc = description.strip()

        # Keep prompt concise, JSON-only, low-temp.
        # Provide the concrete forbidden list (lemmas) and clear rules.
        forbidden_lemmas = [lemmatize_term(t) for t in forbidden]

        prompt = f"""
            You check a game description for rule violations.

            Target word: "{w}"
            Forbidden lemmas (exact words/phrases): {forbidden_lemmas}

            Game rules (return findings only, no prose):
            - The target word itself and ANY same-stem variants are forbidden.
            - Any term from the forbidden lemmas list is forbidden 
            - Any same-stem variant of a forbidden lemma is also forbidden.
            - Avoid spelling circumvention (e.g., "ph0ne" for "phone") or sounds-like hints (e.g., "fone" for "phone").
            - Avoid translation circumvention (e.g., "telefono" for "phone").
            Return ONLY a JSON array of objects, each:
            {{"span": "<exact offending substring from the description>",
                "rule": "<one of: phrase-forbidden | target-stem-forbidden | lemma-forbidden | banned-stem-forbidden | spelling-circumvention | translation-circumvention | sounds-like-hint | near-paraphrase>"}}

            Description:
            \"\"\"{desc}\"\"\"

            Limit to {max_findings} findings.
            """

        findings = []
        if self.llm.backend == "ollama":
            host = self.llm.params.get("host", "http://localhost:11434")
            model = self.llm.params["model"]
            r = requests.post(
                f"{host}/api/generate",
                json={"model": model, "prompt": prompt, "temperature": 0.2, "stream": False, "options": {"num_ctx": 2048}},
                timeout=60
            )
            text = r.json()["response"].strip()
            print("LLM findings raw:", text)  # TODO: testing only - delete
            try:
                findings = json.loads(text)
            except Exception:
                start, end = text.find("["), text.rfind("]")
                findings = json.loads(text[start:end+1]) if start != -1 and end != -1 else []
        else:
            return {"valid": True, "violations": []}

        # Normalize to [(span, rule)] and lowercase spans for consistency
        violations = []
        for f in findings:
            span = (f.get("span") or "").strip()
            rule = (f.get("rule") or "").strip()
            if span and rule:
                violations.append((span, rule))

        return {"valid": len(violations) == 0, "violations": violations}


    def check_description_hybrid(
        self,
        word: str,
        description: str,
        forbidden: List[str],
        use_llm: bool = True
    ) -> Dict:
        """
        Runs deterministic checks first (stems/lemmas/phrases), then optionally
        asks the LLM to catch semantic/obfuscation cases. Merges results.
        """
        det = self.check_description(word, description, forbidden)

        if not use_llm or not self.llm:
            return det

        llm = self.check_description_llm(word, description, forbidden)

        # Merge & deduplicate (case-insensitive by span+rule)
        seen = set()
        merged = []
        for src in (det["violations"] + llm["violations"]):
            key = (src[0].lower(), src[1])
            if key not in seen:
                seen.add(key)
                merged.append(src)

        return {"valid": len(merged) == 0, "violations": merged}


    # ---------- Internals ----------
    def meaning_queries(self, w: str) -> Tuple[List[str], List[str]]:
        """Return query strings and list of glosses(meanings) (for LLM prompting)
        glosses is another word for definition, used for cases of homographs (second - 2d or second(time))
        """
        Q = [w]
        glosses = []
        for s in wn.synsets(w):
            gloss = s.definition()
            Q.append(f"{w} — {gloss}")
            glosses.append(gloss)
        return Q, glosses

    def expand_lexical(self, w: str) -> Tuple[Dict[str, set], Dict[str, set]]:
        """Returns synonyms and antonyms of the world (in this exact order)
        each stored in dictionary with each sysnet as a key 
        and set of synonyms/antonyms (words nod synsets in this case) 
        """
        syn_by_sense, ant_by_sense = {}, {}
        for s in wn.synsets(w): # looping through all meanings of the word - in synsets from nltk form/object
            # each synset represents another meaning and holds within all its synonyms in lemma form - acces is through s.lemmas()
            syn_by_sense[s.name()] = {l.name().replace("_", " ").lower() for l in s.lemmas()}
            ant = set()
            for l in s.lemmas(): # finding antonym for each actual word - lemma 
                ant |= {a.name().replace("_", " ").lower() for a in l.antonyms()}
            ant_by_sense[s.name()] = ant # saving them all accordingly to the current meaning 
        return syn_by_sense, ant_by_sense

    def faiss_neighbors(self, queries: List[str], k: int) -> set:
        """
        Performs a search using faiss module with selected index - in this case graph based
            (collects possible neighbors)
        queiries - list of words and pairs word - gloss used for similiarity search
        k - faiss_topk in config class 
        NOTE: 
        we don't preserve similiarity in this step, 
        we'll do it later after normalizing and adding additional candidates
        """
        # sims is similiarity score, idx is index of item itself
        sims, idxs = self.idx.search(queries, k) # NOTE: faiss takes care of embeddings:) 
        # ensures legitimacy of all retrieved idxs for each query
        # idx = -1 is code for no retrivieng results 
        return {self.idx.items[j] for row in idxs for j in row if j != -1} 

    def _encode(self, term: str) -> np.ndarray:
        # cached sentence-transformer encoding (normalized)
        # We remember the embeddings we’ve already computed, so if we see the same word again, we don’t have to re-calculate it.
        # can potentially save a lot of memory extra usage 
        # NOTE: If we want to simplify the code this we can delete caching part 
        v = self._enc_cache.get(term)
        if v is None:
            v = self.idx.model.encode([term], normalize_embeddings=True, convert_to_numpy=True).astype("float32")[0]
            self._enc_cache[term] = v
        return v

    def cos_w(self, w: str, term: str) -> float:
        # cosine similiarity between the word and llm suggestions
        return float(self._encode(term) @ self._encode(w))

    def rank_pool(self, w: str, pool: set, syns: set, ants: set, llm_terms: set) -> List[Tuple[str, float]]:
        """
        Ranks the candidates by the ranking described in final report 
        syns, ants get higher score, used for check in line 345!
        """
        wv = self._encode(w)
        items = list(pool)
        # encoding and computing a similiarity 
        vecs = np.stack([self._encode(t) for t in items], axis=0)
        cosines = (vecs @ wv)

        # dropping candidates with low similiarity
        kept_items, kept_cos = [], []
        for t, c in zip(items, cosines):
            if (c >= self.cfg.tau_floor) or (t in ants):
                kept_items.append(t)
                kept_cos.append(float(c))

        # computing the score for each candidate(term)
        scored = []
        for t, c in zip(kept_items, kept_cos):
            s = (self.cfg.w_cos * c
                 + self.cfg.w_syn * (t in syns)
                 + self.cfg.w_ant * (t in ants)
                 + self.cfg.w_llm * (t in llm_terms))
            scored.append((t, float(s)))

        # sorting, the higher the score the closer the word, more likely to be banned 
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def mmr_select(self,ranked: list[tuple[str, float]], out_k: int) -> list[str]:
        """
        Stem-aware MMR selection:
        - balances relevance(high score) vs diversity (avoid near-duplicates)
        - prevents stem overlap across selected items (e.g., no 'fire' with 'ring of fire')!
        """
        if not ranked:
            print("Not ranked flag") # TODO: testing only - delete
            return []

        cand_terms = [t for t, _ in ranked] # ranked already are sorted
        cand_vecs = np.stack([self._encode(t) for t in cand_terms], axis=0) # preserving the order

        # selected: list[int] = [] # TODO delete
        selected = [] # for indices of chosen items
        remaining = list(range(len(cand_terms))) # complementary, indices of not-yet-chosen items
        
        # track stems used by already selected items
        # used_stems: set[str] = set() # TODO delete
        used_stems = set()
        # store stem bags for all candidates
        cand_stem_bags = [stem_bag(t) for t in cand_terms]

        while remaining and len(selected) < out_k:
            best_idx, best_val = None, -1e9
            # consider a head slice for speed
            for i in remaining[:128]:
                # skip candidates that share stems with already selected items
                if used_stems and cand_stem_bags[i].intersection(used_stems):
                    continue
                rel = ranked[i][1]  # our ban score
                
                # max similarity to already selected items (diversity term)
                if selected:
                    sims = cand_vecs[i] @ cand_vecs[selected].T # cand_vecs is numpy
                    div = float(np.max(sims))
                else:
                    div = 0.0
                    
                # λ * rel = keep relevance high.
                # (1 – λ) * div = subtract penalty for being too similar to what’s already selected.
                val = self.cfg.mmr_lambda * rel - (1.0 - self.cfg.mmr_lambda) * div
                if val > best_val:
                    best_val, best_idx = val, i

            if best_idx is None:
                # no candidate passed the stem-overlap constraint in this head slice
                if len(remaining) > 128:
                    # drop the head; try next block
                    del remaining[:128]
                    continue
                else:
                    # nothing left that fits the constraint — stop
                    break

            selected.append(best_idx)
            # save stems from the chosen item
            used_stems |= cand_stem_bags[best_idx]
            # remove from remaining
            remaining.remove(best_idx)

        return [cand_terms[i] for i in selected[:out_k]]
    
# הערותתתתת:
"""
host = self.params.get("host", "http://localhost:11434")
Ollama always runs a local HTTP server when it's installed.

By default, it listens at http://localhost:11434.

So unless you explicitly pass a different host in llm_params, it uses that default.
"""