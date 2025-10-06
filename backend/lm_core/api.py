# backend/llm_core/api.py
import os, json, re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AI Service (Words + Description Check)")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL = os.getenv("LLM_MODEL", "phi3:mini")  # use mini by default

# ---------- Schemas ----------
class WordsOut(BaseModel):
    targetWord: str
    forbiddenWords: list[str]

class CheckIn(BaseModel):
    targetWord: str
    forbiddenWords: list[str]
    description: str

class CheckOut(BaseModel):
    ok: bool
    violated: list[str] = []
    reason: str | None = None  # model's explanation (optional)

# ---------- Health ----------
@app.get("/healthz")
def healthz():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        ok = r.status_code == 200
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "model": MODEL}

# ---------- Generate only words ----------
@app.post("/gen_words", response_model=WordsOut)
def gen_words():
    """
    Ask the model to output strict JSON:
    {"targetWord":"...", "forbiddenWords":["...","...","..."]}
    """
    prompt = (
        "Generate JSON for a guessing game with keys exactly: "
        '{"targetWord","forbiddenWords"}.\n'
        "- targetWord: ONE common English noun, one word, lowercase.\n"
        "- forbiddenWords: 3-5 lowercase words strongly related to the target.\n"
        "- Do NOT include the target in forbiddenWords.\n"
        "Return ONLY the compact JSON, no extra text.\n"
    )
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=45,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        # Extract first {...}
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            text = m.group(0)
        data = json.loads(text)
        target = str(data.get("targetWord", "")).strip().lower()
        fwords = [str(w).strip().lower() for w in (data.get("forbiddenWords") or []) if str(w).strip()]
        if not target or not fwords:
            raise ValueError("missing fields")
        if any(target == w for w in fwords):
            raise ValueError("target present in forbiddenWords")
        return WordsOut(targetWord=target, forbiddenWords=fwords)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI gen_words failed: {e}")

# ---------- Check description (no target/forbidden words) ----------
@app.post("/check_description", response_model=CheckOut)
def check_description(body: CheckIn):
    """
    Ask the model to return strict JSON {ok:bool, violated:[...], reason:"..."}.
    The model must mark 'ok=false' if the description includes the target or any forbidden words
    as WHOLE WORDS (case-insensitive).
    """
    target = (body.targetWord or "").strip().lower()
    forb = [w.strip().lower() for w in (body.forbiddenWords or []) if w.strip()]
    desc  = (body.description or "").strip()

    # Local lexical pre-check (fast, deterministic)
    violated = []
    tokens = re.findall(r"[a-zA-Z]+", desc.lower())
    vocab = set(tokens)
    if target in vocab:
        violated.append(target)
    violated.extend([w for w in forb if w in vocab])
    if violated:
        return CheckOut(ok=False, violated=sorted(set(violated)), reason="lexical match")

    # LLM confirmation (in case of punctuation tricks / minor variants)
    sys_prompt = (
        "You are a strict validator. Given a target word, a list of forbidden words, "
        "and a description, determine if the description contains any of the words as "
        "WHOLE WORDS (case-insensitive). Do not consider synonyms or related words—"
        "only EXACT token matches after basic punctuation removal. Return ONLY JSON:\n"
        '{"ok": true/false, "violated": ["w1","w2"], "reason": "short"}'
    )
    user_prompt = json.dumps({
        "targetWord": target,
        "forbiddenWords": forb,
        "description": desc
    }, ensure_ascii=False)

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": f"{sys_prompt}\nInput: {user_prompt}\nOutput JSON:",
                "stream": False,
            },
            timeout=45,
        )
        r.raise_for_status()
        resp = r.json().get("response", "").strip()
        m = re.search(r"\{.*\}", resp, flags=re.S)
        if m:
            resp = m.group(0)
        data = json.loads(resp)
        ok = bool(data.get("ok", False))
        vio = [str(w).strip().lower() for w in (data.get("violated") or []) if str(w).strip()]
        reason = str(data.get("reason") or "").strip() or None
        return CheckOut(ok=ok, violated=vio, reason=reason)
    except Exception as e:
        # If the model fails, fall back to lexical result
        return CheckOut(ok=True, violated=[], reason=f"llm degraded: {e}")
