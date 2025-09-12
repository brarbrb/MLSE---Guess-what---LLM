from typing import Dict, List, Tuple

class ForbiddenAPI:
    # ... keep your existing code ...

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
- Any term from the forbidden lemmas list is forbidden (exact token or exact multiword phrase).
- Any same-stem variant of a forbidden lemma is also forbidden.
- Also flag semantic circumventions: spelling with spaces/punctuation/emojis, translations into other languages, "sounds like"/"rhymes with", or a near-paraphrase that gives the word away.

Return ONLY a JSON array of objects, each:
  {{"span": "<exact offending substring from the description>",
    "rule": "<one of: phrase-forbidden | target-stem-forbidden | lemma-forbidden | banned-stem-forbidden | spelling-circumvention | translation-circumvention | sounds-like-hint | near-paraphrase>"}}

Description:
\"\"\"{desc}\"\"\"

Limit to {max_findings} findings.
"""

        # Use the same backend you configured for generation.
        findings = []
        if self.llm.backend == "ollama":
            import requests, json
            host = self.llm.params.get("host", "http://localhost:11434")
            model = self.llm.params["model"]
            r = requests.post(
                f"{host}/api/generate",
                json={"model": model, "prompt": prompt, "temperature": 0.2, "stream": False, "options": {"num_ctx": 2048}},
                timeout=60
            )
            text = r.json()["response"].strip()
            try:
                findings = json.loads(text)
            except Exception:
                start, end = text.find("["), text.rfind("]")
                findings = json.loads(text[start:end+1]) if start != -1 and end != -1 else []
        elif self.llm.backend == "openai":
            import json
            msgs = [
                {"role": "system", "content": "Reply ONLY with a JSON array of objects as specified."},
                {"role": "user", "content": prompt},
            ]
            r = self.llm._client.chat.completions.create(
                model=self.llm.params["model"], messages=msgs, temperature=0.2, max_tokens=300
            )
            findings = json.loads(r.choices[0].message.content.strip())
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


# Build index & API as before (ollama backend configured)
banned = api.generate_forbidden("volcano", out_k=16)

desc = "A mountain that erupts with 🔥, rhymes with 'polcano', ring of fire."
print(api.check_description("volcano", desc, banned))          # deterministic only
print(api.check_description_hybrid("volcano", desc, banned))   # deterministic + LLM
